"""Unit tests for the S-1 parser."""

from pathlib import Path

import pytest

from agent.parser import S1Parser

FIXTURE = Path(__file__).parent / "fixtures" / "sample_s1_excerpt.html"


@pytest.fixture
def parser():
    html = FIXTURE.read_text(encoding="utf-8")
    return S1Parser(html, company="Acme Corp")


def test_list_sections_returns_known_sections(parser):
    sections = parser.list_sections()
    assert len(sections) > 0
    # Should find at least business, mda, and risk_factors
    assert any("business" in s for s in sections)
    assert any("risk" in s for s in sections)


def test_get_section_business(parser):
    text = parser.get_section("business")
    assert "Acme" in text or "enterprise" in text.lower()


def test_get_section_mda(parser):
    text = parser.get_section("mda")
    assert "revenue" in text.lower() or "312" in text


def test_get_section_risk_factors(parser):
    text = parser.get_section("risk_factors")
    assert "risk" in text.lower() or "loss" in text.lower()


def test_get_section_missing_returns_message(parser):
    text = parser.get_section("nonexistent_section_xyz")
    assert "not found" in text.lower() or "available" in text.lower()


def test_get_section_full_returns_text(parser):
    text = parser.get_section("full")
    assert len(text) > 100
    assert "Acme" in text


def test_get_financial_table_income_statement(parser):
    text = parser.get_financial_table("income_statement")
    # Should find revenue data
    assert "revenue" in text.lower() or "Revenue" in text


def test_get_financial_table_balance_sheet(parser):
    text = parser.get_financial_table("balance_sheet")
    assert "assets" in text.lower() or "equity" in text.lower()


def test_get_financial_table_cash_flow(parser):
    text = parser.get_financial_table("cash_flow")
    assert "activities" in text.lower() or "cash" in text.lower()


def test_get_financial_table_unknown_type(parser):
    text = parser.get_financial_table("xyzunknown")
    assert "no" in text.lower() and "found" in text.lower()


def test_get_summary_metadata(parser):
    meta = parser.get_summary_metadata()
    assert meta["company"] == "Acme Corp"
    assert meta["total_chars"] > 0
    assert isinstance(meta["table_count"], int)
    assert meta["table_count"] >= 3
    assert isinstance(meta["sections_found"], list)


def test_chunking_truncates_large_sections():
    big_html = f"<h2>BUSINESS</h2><p>{'x' * 200_000}</p>"
    p = S1Parser(big_html, "BigCo")
    text = p.get_section("business")
    assert "TRUNCATED" in text


def test_parser_handles_empty_html():
    p = S1Parser("", "EmptyCo")
    sections = p.list_sections()
    assert isinstance(sections, list)
