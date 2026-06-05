"""SEC EDGAR S-1 fetcher — search by ticker or company name, download filing."""

import re
import time

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from config import EDGAR_USER_AGENT, VERBOSE

EDGAR_BASE = "https://data.sec.gov"
EDGAR_EFTS = "https://efts.sec.gov/LATEST/search-index"
EDGAR_ARCHIVES = "https://www.sec.gov/Archives/edgar/data"
EDGAR_COMPANY_TICKERS = "https://data.sec.gov/files/company_tickers.json"

HEADERS = {
    "User-Agent": EDGAR_USER_AGENT,
    "Accept-Encoding": "gzip, deflate",
    "Accept": "application/json, text/html, */*",
}

# EDGAR rate limit: ~10 req/s. We stay well below.
REQUEST_DELAY = 0.15

# Only look at S-1s filed from this date onwards
MIN_FILING_DATE = "2024-01-01"


class FilingNotFoundError(Exception):
    pass


class EDGARFetcher:
    """Fetches S-1 filings from SEC EDGAR."""

    def __init__(self):
        self.client = httpx.Client(
            headers=HEADERS,
            timeout=60.0,
            follow_redirects=True,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def find_s1(self, query: str, is_ticker: bool = False) -> dict:
        """Return a dict with company metadata and the full S-1 HTML content."""
        if is_ticker:
            return self._find_by_ticker(query.upper())
        return self._find_by_name(query)

    # ------------------------------------------------------------------
    # Search paths
    # ------------------------------------------------------------------

    def _find_by_ticker(self, ticker: str) -> dict:
        cik = self._resolve_ticker_to_cik(ticker)
        return self._latest_s1_for_cik(cik, ticker)

    def _find_by_name(self, name: str) -> dict:
        """Search EDGAR full-text search for the most recent S-1 by name."""
        if VERBOSE:
            print(f"[fetcher] Searching EDGAR for S-1: '{name}'")

        # Try quoted search first (exact entity name match)
        params = {
            "q": f'"{name}"',
            "forms": "S-1",
            "dateRange": "custom",
            "startdt": MIN_FILING_DATE,
        }
        hits = self._efts_search(params)

        if not hits:
            # Retry without quotes — broader keyword match
            params["q"] = name
            hits = self._efts_search(params)

        if not hits:
            # Final attempt: search without date constraint
            del params["dateRange"]
            del params["startdt"]
            hits = self._efts_search(params)

        if not hits:
            raise FilingNotFoundError(
                f"No S-1 filings found for '{name}' on EDGAR. "
                "The company may not have filed yet, or try a different name variant."
            )

        source = hits[0]["_source"]
        if VERBOSE:
            print(
                f"[fetcher] Found: {source.get('entity_name')} "
                f"filed {source.get('file_date')}"
            )
        return self._fetch_from_hit(source)

    # ------------------------------------------------------------------
    # CIK resolution
    # ------------------------------------------------------------------

    def _resolve_ticker_to_cik(self, ticker: str) -> str:
        """Map ticker symbol → zero-padded 10-digit CIK."""
        if VERBOSE:
            print(f"[fetcher] Resolving ticker '{ticker}' to CIK")
        resp = self._get(EDGAR_COMPANY_TICKERS)
        data = resp.json()
        for entry in data.values():
            if entry.get("ticker", "").upper() == ticker:
                return str(entry["cik_str"]).zfill(10)
        raise FilingNotFoundError(
            f"Ticker '{ticker}' not found in EDGAR company tickers."
        )

    # ------------------------------------------------------------------
    # Filing discovery via CIK
    # ------------------------------------------------------------------

    def _latest_s1_for_cik(self, cik: str, label: str) -> dict:
        """Pull the most recent S-1 from the submissions JSON for a CIK."""
        url = f"{EDGAR_BASE}/submissions/CIK{cik}.json"
        resp = self._get(url)
        sub = resp.json()
        company_name = sub.get("name", label)

        filings = sub.get("filings", {}).get("recent", {})
        forms = filings.get("form", [])
        accessions = filings.get("accessionNumber", [])
        dates = filings.get("filingDate", [])
        primary_docs = filings.get("primaryDocument", [])

        for i, form in enumerate(forms):
            if form == "S-1":
                return self._download_filing(
                    cik=cik.lstrip("0"),
                    accession=accessions[i],
                    date=dates[i],
                    company=company_name,
                    primary_doc=primary_docs[i],
                )

        raise FilingNotFoundError(
            f"No S-1 filing found for '{label}' (CIK {cik}). "
            "The company may not have filed or may be private."
        )

    # ------------------------------------------------------------------
    # Filing download
    # ------------------------------------------------------------------

    def _fetch_from_hit(self, source: dict) -> dict:
        """Download S-1 from an EDGAR full-text search hit."""
        company = source.get("entity_name", "Unknown")
        date = source.get("file_date", "")
        accession = source.get("accession_no", "")
        ciks = source.get("ciks", [""])
        cik = ciks[0].lstrip("0") if ciks else ""

        primary_doc = self._get_primary_document(cik, accession)
        return self._download_filing(cik, accession, date, company, primary_doc)

    def _get_primary_document(self, cik: str, accession: str) -> str:
        """Fetch the filing index and return the primary document filename."""
        acc_clean = accession.replace("-", "")
        index_url = (
            f"{EDGAR_ARCHIVES}/{cik}/{acc_clean}/{accession}-index.json"
        )
        try:
            resp = self._get(index_url)
            index = resp.json()
            documents = index.get("documents", [])
            # Prefer explicit S-1 type
            for doc in documents:
                if doc.get("type") in ("S-1", "S-1/A"):
                    return doc["filename"]
            # Fallback: first .htm that isn't an exhibit
            for doc in documents:
                fn = doc.get("filename", "").lower()
                if fn.endswith(".htm") and not fn.startswith("ex"):
                    return doc["filename"]
            # Last fallback: any .htm
            for doc in documents:
                if doc.get("filename", "").lower().endswith(".htm"):
                    return doc["filename"]
        except Exception:
            pass

        return f"{accession}.htm"

    def _download_filing(
        self,
        cik: str,
        accession: str,
        date: str,
        company: str,
        primary_doc: str,
    ) -> dict:
        """Download (or load from cache) the S-1 HTML document."""
        import config as _cfg  # read at call time so monkeypatching works in tests

        acc_clean = accession.replace("-", "")
        doc_url = f"{EDGAR_ARCHIVES}/{cik}/{acc_clean}/{primary_doc}"

        safe_name = re.sub(r"[^\w\-]", "_", company)
        cache_path = _cfg.CACHE_DIR / f"{safe_name}_{date}.html"

        if _cfg.EDGAR_CACHE and cache_path.exists():
            if VERBOSE:
                print(f"[fetcher] Loading from cache: {cache_path}")
            content = cache_path.read_text(encoding="utf-8", errors="replace")
        else:
            if VERBOSE:
                print(f"[fetcher] Downloading S-1: {doc_url}")
            resp = self._get(doc_url)
            content = resp.text
            if _cfg.EDGAR_CACHE:
                cache_path.write_text(content, encoding="utf-8", errors="replace")
                if VERBOSE:
                    print(f"[fetcher] Cached to: {cache_path}")

        return {
            "company": company,
            "filing_date": date,
            "accession": accession,
            "cik": cik,
            "url": doc_url,
            "content": content,
            "char_count": len(content),
        }

    # ------------------------------------------------------------------
    # HTTP helpers
    # ------------------------------------------------------------------

    def _efts_search(self, params: dict) -> list:
        """Call EDGAR full-text search and return list of hits."""
        resp = self._get(EDGAR_EFTS, params=params)
        data = resp.json()
        return data.get("hits", {}).get("hits", [])

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
    def _get(self, url: str, params: dict | None = None) -> httpx.Response:
        time.sleep(REQUEST_DELAY)
        resp = self.client.get(url, params=params)
        resp.raise_for_status()
        return resp

    def close(self):
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
