"""Unit tests for the EDGAR fetcher (network calls are mocked)."""

from unittest.mock import MagicMock, patch

import pytest

from agent.fetcher import EDGARFetcher, FilingNotFoundError


@pytest.fixture
def fetcher():
    f = EDGARFetcher()
    yield f
    f.close()


# ------------------------------------------------------------------
# Ticker resolution
# ------------------------------------------------------------------


def test_resolve_known_ticker_structure(fetcher):
    """_resolve_ticker_to_cik should handle a well-formed tickers JSON."""
    mock_data = {
        "0": {"cik_str": 1234567, "ticker": "ACME", "title": "Acme Corp"},
        "1": {"cik_str": 9876543, "ticker": "SMPL", "title": "Sample Inc"},
    }
    mock_resp = MagicMock()
    mock_resp.json.return_value = mock_data

    with patch.object(fetcher, "_get", return_value=mock_resp):
        cik = fetcher._resolve_ticker_to_cik("ACME")
    assert cik == "0001234567"


def test_resolve_unknown_ticker_raises(fetcher):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {}
    with patch.object(fetcher, "_get", return_value=mock_resp):
        with pytest.raises(FilingNotFoundError):
            fetcher._resolve_ticker_to_cik("ZZZZ")


# ------------------------------------------------------------------
# EFTS search
# ------------------------------------------------------------------


def test_efts_search_returns_hits(fetcher):
    mock_data = {
        "hits": {
            "hits": [
                {
                    "_source": {
                        "entity_name": "Acme Corp",
                        "file_date": "2025-03-01",
                        "form_type": "S-1",
                        "accession_no": "0001234567-25-000001",
                        "ciks": ["0001234567"],
                    }
                }
            ]
        }
    }
    mock_resp = MagicMock()
    mock_resp.json.return_value = mock_data
    with patch.object(fetcher, "_get", return_value=mock_resp):
        hits = fetcher._efts_search({"q": "Acme", "forms": "S-1"})
    assert len(hits) == 1
    assert hits[0]["_source"]["entity_name"] == "Acme Corp"


def test_efts_search_returns_empty_on_no_results(fetcher):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"hits": {"hits": []}}
    with patch.object(fetcher, "_get", return_value=mock_resp):
        hits = fetcher._efts_search({"q": "NonexistentCo", "forms": "S-1"})
    assert hits == []


# ------------------------------------------------------------------
# Primary document extraction
# ------------------------------------------------------------------


def test_get_primary_document_finds_s1_type(fetcher):
    index = {
        "documents": [
            {"filename": "exhibit1.htm", "type": "EX-99"},
            {"filename": "s1main.htm", "type": "S-1"},
        ]
    }
    mock_resp = MagicMock()
    mock_resp.json.return_value = index
    with patch.object(fetcher, "_get", return_value=mock_resp):
        doc = fetcher._get_primary_document("1234567", "0001234567-25-000001")
    assert doc == "s1main.htm"


def test_get_primary_document_fallback_to_htm(fetcher):
    index = {
        "documents": [
            {"filename": "first.htm", "type": "GRAPHIC"},
            {"filename": "second.htm", "type": "OTHER"},
        ]
    }
    mock_resp = MagicMock()
    mock_resp.json.return_value = index
    with patch.object(fetcher, "_get", return_value=mock_resp):
        doc = fetcher._get_primary_document("1234567", "0001234567-25-000001")
    assert doc.endswith(".htm")


# ------------------------------------------------------------------
# Download + cache
# ------------------------------------------------------------------


def test_download_filing_uses_cache(fetcher, tmp_path):
    import config

    original = config.CACHE_DIR
    config.CACHE_DIR = tmp_path

    cache_file = tmp_path / "Acme_Corp_2025-03-01.html"
    cache_file.write_text("<html>cached content</html>", encoding="utf-8")

    result = fetcher._download_filing(
        cik="1234567",
        accession="0001234567-25-000001",
        date="2025-03-01",
        company="Acme Corp",
        primary_doc="s1.htm",
    )
    assert result["content"] == "<html>cached content</html>"
    config.CACHE_DIR = original


def test_filing_not_found_error_message():
    err = FilingNotFoundError("No S-1 found for 'TestCo'")
    assert "TestCo" in str(err)
