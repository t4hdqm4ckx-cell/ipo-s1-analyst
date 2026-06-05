"""Unit tests for the pre-scan analyzer module."""

from pathlib import Path

import pytest

from agent.analyzer import (
    build_context_summary,
    extract_financial_signals,
    extract_risk_keywords,
)
from agent.parser import S1Parser

FIXTURE = Path(__file__).parent / "fixtures" / "sample_s1_excerpt.html"


@pytest.fixture
def parser():
    html = FIXTURE.read_text(encoding="utf-8")
    return S1Parser(html, company="Acme Corp")


@pytest.fixture
def filing(parser):
    return {
        "company": "Acme Corp",
        "filing_date": "2025-03-01",
        "url": "https://sec.gov/...",
    }


def test_extract_financial_signals_returns_dict(parser):
    signals = extract_financial_signals(parser)
    assert isinstance(signals, dict)
    assert "dollar_amounts_found" in signals
    assert "growth_rate_mentions" in signals
    assert "key_percentages" in signals


def test_financial_signals_finds_dollar_amounts(parser):
    signals = extract_financial_signals(parser)
    # Fixture has $312.4M, $450M, $142.3M, etc.
    amounts = signals["dollar_amounts_found"]
    assert isinstance(amounts, list)
    assert any("312" in a or "450" in a or "142" in a for a in amounts)


def test_extract_risk_keywords_returns_list(parser):
    keywords = extract_risk_keywords(parser)
    assert isinstance(keywords, list)


def test_extract_risk_keywords_detects_net_losses(parser):
    # Fixture mentions "history of net losses"
    keywords = extract_risk_keywords(parser)
    assert any("loss" in kw.lower() or "profitab" in kw.lower() for kw in keywords)


def test_build_context_summary_returns_string(parser, filing):
    summary = build_context_summary(parser, filing)
    assert isinstance(summary, str)
    assert len(summary) > 50


def test_build_context_summary_contains_company(parser, filing):
    summary = build_context_summary(parser, filing)
    assert "Acme Corp" in summary


def test_build_context_summary_contains_financial_section(parser, filing):
    summary = build_context_summary(parser, filing)
    assert "Financial signals" in summary or "financial" in summary.lower()


def test_extract_financial_signals_empty_doc():
    p = S1Parser("", "EmptyCo")
    signals = extract_financial_signals(p)
    assert isinstance(signals["dollar_amounts_found"], list)
    assert isinstance(signals["growth_rate_mentions"], list)
