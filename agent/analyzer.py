"""
Pre-processing helpers that extract structured financial signals from the S-1
before the agentic loop starts. These give Claude a quantitative head-start.
"""

import re
from typing import Optional

from agent.parser import S1Parser


def _find_dollar_amounts(text: str) -> list[str]:
    """Extract dollar amounts (e.g. '$312.4 million', '$1.2B') from text."""
    pattern = r"\$[\d,]+\.?\d*\s*(?:million|billion|thousand|M|B|K)?"
    return re.findall(pattern, text, re.IGNORECASE)


def _find_percentages(text: str) -> list[str]:
    """Extract percentages from text."""
    return re.findall(r"\d+\.?\d*\s*%", text)


def _find_growth_rates(text: str) -> list[str]:
    """Extract YoY or sequential growth references."""
    pattern = (
        r"(?:increased?|decreased?|grew?|declined?|grew?|rose?|fell?)"
        r"[^.]*?\d+\.?\d*\s*%"
    )
    return re.findall(pattern, text, re.IGNORECASE)[:10]


def extract_financial_signals(parser: S1Parser) -> dict:
    """
    Extract lightweight financial signals from the S-1 to seed the agent context.
    Returns a dict summary Claude can reference without re-reading the whole doc.
    """
    mda_text = parser.get_section("mda")
    summary_text = parser.get_section("summary")
    financials_text = parser.get_section("financials")

    combined = f"{summary_text}\n\n{mda_text}\n\n{financials_text}"

    dollar_amounts = _find_dollar_amounts(combined)
    growth_rates = _find_growth_rates(combined)
    percentages = _find_percentages(mda_text)[:20]

    # Try to extract IPO price range
    price_range = re.findall(
        r"\$\d+\.?\d*\s*(?:to|and|-)\s*\$\d+\.?\d*\s*per share",
        combined,
        re.IGNORECASE,
    )

    # Shares offered
    shares_offered = re.findall(
        r"[\d,]+(?:\.\d+)?\s*(?:million\s+)?shares\s+(?:of\s+)?(?:common\s+stock\s+)?(?:in\s+this\s+offering|being\s+offered)",
        combined,
        re.IGNORECASE,
    )

    return {
        "dollar_amounts_found": list(set(dollar_amounts))[:15],
        "growth_rate_mentions": growth_rates,
        "key_percentages": list(set(percentages))[:15],
        "ipo_price_range": price_range[:2] if price_range else [],
        "shares_offered_mentions": shares_offered[:2] if shares_offered else [],
    }


def extract_risk_keywords(parser: S1Parser) -> list[str]:
    """
    Scan Risk Factors for the highest-signal risk phrases.
    Returns a short list to seed the agent's risk analysis.
    """
    risk_text = parser.get_section("risk_factors")
    if "not found" in risk_text.lower():
        return []

    high_signal_patterns = [
        r"going[- ]concern",
        r"material weakness",
        r"significant doubt",
        r"unable to achieve profitability",
        r"history of net losses",
        r"key man",
        r"single customer",
        r"customer concentration",
        r"regulatory approval",
        r"litigation",
        r"cybersecurity",
        r"data breach",
        r"dilut",
        r"dual[- ]class",
        r"no voting rights",
        r"government contract",
        r"export control",
    ]

    found = []
    for pat in high_signal_patterns:
        if re.search(pat, risk_text, re.IGNORECASE):
            found.append(pat.replace(r"[- ]", "-").replace(r"[- ]", " "))

    return found


def build_context_summary(parser: S1Parser, filing: dict) -> str:
    """
    Build a concise pre-analysis context block to prepend to the agent's
    first message. Saves early tool calls for higher-value investigation.
    """
    meta = parser.get_summary_metadata()
    signals = extract_financial_signals(parser)
    risk_kw = extract_risk_keywords(parser)

    lines = [
        f"## Pre-scan Summary for {filing['company']}",
        f"Filing date: {filing['filing_date']} | "
        f"Doc size: {meta['total_chars']:,} chars | "
        f"{meta['table_count']} tables",
        f"Sections parsed: {', '.join(meta['sections_found']) or 'none'}",
        "",
        "### Financial signals detected",
        f"Dollar amounts: {', '.join(signals['dollar_amounts_found'][:8]) or 'none found'}",
        f"Growth rate mentions: {'; '.join(signals['growth_rate_mentions'][:4]) or 'none found'}",
        f"Key percentages: {', '.join(signals['key_percentages'][:8]) or 'none found'}",
    ]

    if signals["ipo_price_range"]:
        lines.append(f"IPO price range: {', '.join(signals['ipo_price_range'])}")

    if risk_kw:
        lines.append("")
        lines.append(f"### High-signal risk keywords: {', '.join(risk_kw)}")

    return "\n".join(lines)
