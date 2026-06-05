"""S-1 document parser — extracts named sections and financial tables from HTML."""

import re
from typing import Optional

from bs4 import BeautifulSoup, Tag

from config import MAX_SECTION_CHARS, VERBOSE

# Canonical section names → patterns that identify them in S-1 headers
SECTION_PATTERNS: dict[str, list[str]] = {
    "summary": [
        r"prospectus\s+summary",
        r"^summary$",
        r"summary\s+of\s+the\s+offering",
    ],
    "risk_factors": [
        r"risk\s+factors",
    ],
    "use_of_proceeds": [
        r"use\s+of\s+proceeds",
    ],
    "dilution": [
        r"^dilution$",
        r"dilution\s+of",
    ],
    "capitalization": [
        r"^capitalization$",
        r"capitalization\s+and\s+indebtedness",
    ],
    "mda": [
        r"management.{0,10}s?\s+discussion",
        r"management.{0,10}s?\s+analysis",
        r"\bmd&a\b",
    ],
    "business": [
        r"^business$",
        r"our\s+business",
        r"description\s+of\s+business",
    ],
    "competition": [
        r"^competition$",
        r"competitive\s+(landscape|environment|position)",
    ],
    "management": [
        r"^management$",
        r"directors.{0,20}executive\s+officers",
        r"executive\s+officers\s+and\s+directors",
    ],
    "compensation": [
        r"executive\s+compensation",
        r"compensation\s+discussion",
    ],
    "principal_stockholders": [
        r"principal\s+(and\s+selling\s+)?stockholders",
        r"beneficial\s+ownership",
        r"security\s+ownership",
    ],
    "related_party": [
        r"related.{0,10}party\s+transactions",
        r"certain\s+relationships",
    ],
    "underwriting": [
        r"^underwriting$",
        r"plan\s+of\s+distribution",
    ],
    "financials": [
        r"financial\s+statements",
        r"consolidated\s+balance\s+sheet",
        r"consolidated\s+statement",
        r"selected\s+financial\s+data",
        r"selected\s+consolidated\s+financial",
    ],
    "notes_to_financials": [
        r"notes\s+to\s+(consolidated\s+)?financial",
    ],
    "selected_financial_data": [
        r"selected\s+(consolidated\s+)?financial\s+(data|information)",
    ],
    "dividend_policy": [
        r"dividend\s+policy",
    ],
    "lock_up": [
        r"lock.{0,5}up\s+agreements?",
        r"transfer\s+restrictions",
    ],
    "corporate_governance": [
        r"corporate\s+governance",
        r"board\s+of\s+directors",
    ],
}

# Financial table keywords → used when extracting specific tables
TABLE_KEYWORDS: dict[str, list[str]] = {
    "income_statement": [
        "revenue",
        "net revenue",
        "total revenue",
        "cost of revenue",
        "gross profit",
        "operating income",
        "net income",
        "net loss",
        "earnings per share",
        "loss per share",
    ],
    "balance_sheet": [
        "total assets",
        "total liabilities",
        "cash and cash equivalents",
        "stockholders",
        "shareholders",
        "total equity",
    ],
    "cash_flow": [
        "operating activities",
        "investing activities",
        "financing activities",
        "net change in cash",
        "capital expenditures",
    ],
    "key_metrics": [
        "monthly active",
        "daily active",
        "users",
        "customers",
        "gross merchandise",
        "gmv",
        "arr",
        "mrr",
        "backlog",
        "contracted",
        "revenue per",
    ],
}


class S1Parser:
    """Parses a raw S-1 HTML document into structured sections."""

    def __init__(self, html: str, company: str = ""):
        self.company = company
        self.soup = BeautifulSoup(html, "lxml")
        self._sections: dict[str, str] = {}
        self._parsed = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_section(self, name: str) -> str:
        """Return text content of a named section, chunked to MAX_SECTION_CHARS."""
        if not self._parsed:
            self._parse_all_sections()
        name = name.lower().strip()
        if name == "full":
            return self._get_full_text()
        text = self._sections.get(name, "")
        if not text:
            for key, val in self._sections.items():
                if name in key or key in name:
                    text = val
                    break
        if not text:
            available = ", ".join(self._sections.keys()) or "none parsed"
            return f"Section '{name}' not found. Available sections: {available}"
        return self._chunk(text)

    def list_sections(self) -> list[str]:
        if not self._parsed:
            self._parse_all_sections()
        return list(self._sections.keys())

    def get_financial_table(self, table_type: str) -> str:
        """Extract text representation of financial tables by type."""
        if not self._parsed:
            self._parse_all_sections()
        keywords = TABLE_KEYWORDS.get(table_type.lower(), [])
        tables = self.soup.find_all("table")
        matched: list[str] = []
        for tbl in tables:
            text = tbl.get_text(" ", strip=True).lower()
            if any(kw in text for kw in keywords):
                matched.append(self._table_to_text(tbl))
                if len("\n\n".join(matched)) > MAX_SECTION_CHARS:
                    break
        if not matched:
            return f"No {table_type} tables found in the filing."
        return self._chunk("\n\n---\n\n".join(matched))

    def get_summary_metadata(self) -> dict:
        """Return lightweight metadata: company, sections found, doc length."""
        if not self._parsed:
            self._parse_all_sections()
        return {
            "company": self.company,
            "sections_found": self.list_sections(),
            "total_chars": len(self.soup.get_text()),
            "table_count": len(self.soup.find_all("table")),
        }

    def word_count(self) -> int:
        """Approximate word count of the full document."""
        return len(self.soup.get_text().split())

    def search_text(self, keyword: str, context_chars: int = 300) -> list[str]:
        """
        Find all occurrences of a keyword and return surrounding context snippets.
        Useful for targeted lookups (e.g. searching for 'going concern').
        """
        full_text = self.soup.get_text("\n", strip=True)
        results = []
        lower = full_text.lower()
        kw = keyword.lower()
        pos = 0
        while True:
            idx = lower.find(kw, pos)
            if idx == -1:
                break
            start = max(0, idx - context_chars // 2)
            end = min(len(full_text), idx + len(keyword) + context_chars // 2)
            snippet = full_text[start:end].strip()
            results.append(snippet)
            pos = idx + len(keyword)
            if len(results) >= 5:
                break
        return results

    # ------------------------------------------------------------------
    # Section extraction
    # ------------------------------------------------------------------

    def _parse_all_sections(self):
        """Walk the document, detect section headers, extract content."""
        self._parsed = True
        text_blocks = self._extract_text_blocks()
        current_section: Optional[str] = None
        current_buf: list[str] = []

        for heading, body in text_blocks:
            matched = self._match_section(heading) if heading else None
            if matched:
                if current_section and current_buf:
                    self._sections[current_section] = "\n".join(current_buf).strip()
                current_section = matched
                current_buf = [heading or ""]
            elif current_section:
                current_buf.append(body)

        if current_section and current_buf:
            self._sections[current_section] = "\n".join(current_buf).strip()

        if VERBOSE:
            print(f"[parser] Sections found: {list(self._sections.keys())}")

    def _extract_text_blocks(self) -> list[tuple[Optional[str], str]]:
        """
        Yield (heading_text, body_text) pairs from the soup.
        Heading is None for non-header elements.
        """
        blocks: list[tuple[Optional[str], str]] = []
        for el in self.soup.find_all(["h1", "h2", "h3", "h4", "p", "div", "table"]):
            if el.name in ("h1", "h2", "h3", "h4"):
                text = el.get_text(" ", strip=True)
                if text:
                    blocks.append((text, text))
            elif el.name == "table":
                blocks.append((None, self._table_to_text(el)))
            else:
                text = el.get_text(" ", strip=True)
                if not text:
                    continue
                style = el.get("style", "") or ""
                is_bold = (
                    "font-weight:bold" in style.replace(" ", "")
                    or "font-weight: bold" in style
                    or bool(el.find("b"))
                    or bool(el.find("strong"))
                )
                is_upper = text.isupper() and len(text) < 120
                if (is_bold or is_upper) and len(text) < 150:
                    blocks.append((text, text))
                else:
                    blocks.append((None, text))
        return blocks

    def _match_section(self, heading: str) -> Optional[str]:
        """Return canonical section name if heading matches a pattern."""
        h = heading.lower().strip()
        for section, patterns in SECTION_PATTERNS.items():
            for pat in patterns:
                if re.search(pat, h, re.IGNORECASE):
                    return section
        return None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _table_to_text(self, tbl: Tag) -> str:
        """Convert an HTML table to a readable pipe-delimited string."""
        rows = []
        for tr in tbl.find_all("tr"):
            cells = [td.get_text(" ", strip=True) for td in tr.find_all(["td", "th"])]
            if any(cells):
                rows.append(" | ".join(cells))
        return "\n".join(rows)

    def _get_full_text(self) -> str:
        text = self.soup.get_text("\n", strip=True)
        return self._chunk(text)

    @staticmethod
    def _chunk(text: str) -> str:
        """Truncate to MAX_SECTION_CHARS with a clear notice if truncated."""
        if len(text) <= MAX_SECTION_CHARS:
            return text
        note = (
            f"\n\n[TRUNCATED — showing first {MAX_SECTION_CHARS:,} of "
            f"{len(text):,} characters. Call get_section again with a more "
            "specific section name to get later content.]"
        )
        return text[:MAX_SECTION_CHARS] + note
