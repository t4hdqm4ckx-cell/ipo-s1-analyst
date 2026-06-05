"""Unit tests for the Markdown report assembler."""

from pathlib import Path

import pytest

from agent.reporter import assemble_report, save_report


SAMPLE_FINDINGS = {
    "company_name": "Acme Corp",
    "filing_date": "2025-03-01",
    "executive_summary": (
        "Acme Corp is a high-growth enterprise SaaS business with 67% YoY revenue "
        "growth and improving unit economics. The IPO raises $450M at a 12x EV/Revenue "
        "multiple, which appears fair relative to peers given the growth trajectory."
    ),
    "business_overview": "Cloud-based enterprise data management platform serving 5,000+ enterprises.",
    "products_and_services": "AcmeCloud: real-time data sync, analytics, workflow automation.",
    "revenue_model": "Subscription licenses (91% of rev) + professional services.",
    "financial_analysis": "Revenue: $312.4M (+67% YoY). Gross margin: 74%. Net loss: $142.3M.",
    "key_metrics": "ARR: $320M. NDR: 128%. Customers: 5,000+.",
    "valuation": "IPO at ~$3.75B EV implies 12x EV/Revenue on FY2024 revenue. Fair for 67% growth.",
    "comparable_companies": "Snowflake (18x), Databricks (est. 15x), Palantir (10x).",
    "competitive_landscape": "Competes with SAP, Oracle (legacy), Snowflake, Palantir (cloud-native).",
    "moat_analysis": "High switching costs, network effects in data layer, 128% NDR indicates strong retention.",
    "swot": {
        "strengths": ["67% revenue growth", "74% gross margin", "128% NRR"],
        "weaknesses": ["$142M net loss", "High sales & marketing spend (52% of rev)"],
        "opportunities": ["International expansion (currently 60% US)", "AI/ML upsell"],
        "threats": ["Hyperscaler competition (AWS, Azure, GCP)", "Macro-driven IT budget cuts"],
    },
    "funding_history": "Raised $680M across 5 rounds. Series E at $2.1B valuation (2024).",
    "key_investors": "Accel Partners (14.5%), Sequoia Capital (12.2%), General Atlantic (9.9%).",
    "use_of_proceeds": "$200M R&D, $150M sales/marketing, remainder for working capital.",
    "cap_table_summary": "CEO retains 8.2%. Top 3 VCs hold 36.6%. Significant dilution in IPO.",
    "risk_flags": [
        "History of net losses ($142M in FY2024); no profitability timeline disclosed.",
        "Key-man dependency on CEO/founder John Smith.",
        "80% of revenue concentrated in North America.",
    ],
    "management_assessment": "Experienced team. CEO founded 2 prior SaaS companies. CFO ex-Workday.",
    "bull_case": "Accelerating growth, international expansion, and AI upsell drive 80%+ revenue CAGR. IPO doubles in 18 months.",
    "base_case": "Growth moderates to 45% as market matures. Stock flat to +30% over 2 years.",
    "bear_case": "Enterprise spending slowdown. Growth decelerates to sub-20%. Stock re-rates to 6x. -40% downside.",
    "investment_recommendation": "BUY",
    "recommendation_rationale": (
        "For an investor with moderate-to-high risk appetite, Acme Corp represents a compelling "
        "IPO. The 67% revenue growth, 74% gross margin, and 128% NRR are top-decile metrics. "
        "At 12x EV/Revenue, the valuation leaves room for multiple expansion if growth holds. "
        "Losses are acceptable given the growth trajectory and strong unit economics. Buy."
    ),
    "key_catalysts": ["International launch Q3 2025", "AI feature release H2 2025"],
    "key_risks_to_thesis": ["Enterprise spending freeze", "Hyperscaler bundling"],
    "_model": "claude-sonnet-4-6",
}

SAMPLE_FILING = {
    "company": "Acme Corp",
    "filing_date": "2025-03-01",
    "url": "https://www.sec.gov/Archives/edgar/data/1234567/000123456725000001/s1.htm",
}


def test_assemble_report_returns_string():
    report = assemble_report(SAMPLE_FINDINGS, SAMPLE_FILING)
    assert isinstance(report, str)
    assert len(report) > 500


def test_report_contains_company_name():
    report = assemble_report(SAMPLE_FINDINGS, SAMPLE_FILING)
    assert "Acme Corp" in report


def test_report_contains_recommendation():
    report = assemble_report(SAMPLE_FINDINGS, SAMPLE_FILING)
    assert "BUY" in report


def test_report_contains_all_sections():
    report = assemble_report(SAMPLE_FINDINGS, SAMPLE_FILING)
    required = [
        "Executive Summary",
        "Business Overview",
        "Financial Analysis",
        "Valuation",
        "Competitive Landscape",
        "SWOT",
        "Funding History",
        "Use of Proceeds",
        "Risk Flags",
        "Investment Conclusion",
    ]
    for section in required:
        assert section in report, f"Missing section: {section}"


def test_report_contains_swot_subsections():
    report = assemble_report(SAMPLE_FINDINGS, SAMPLE_FILING)
    assert "Strengths" in report
    assert "Weaknesses" in report
    assert "Opportunities" in report
    assert "Threats" in report


def test_report_contains_bull_base_bear():
    report = assemble_report(SAMPLE_FINDINGS, SAMPLE_FILING)
    assert "Bull Case" in report
    assert "Base Case" in report
    assert "Bear Case" in report


def test_report_contains_disclaimer():
    report = assemble_report(SAMPLE_FINDINGS, SAMPLE_FILING)
    assert "informational purposes only" in report.lower()


def test_save_report_creates_file(tmp_path):
    import config
    original = config.REPORTS_DIR
    config.REPORTS_DIR = tmp_path

    report = assemble_report(SAMPLE_FINDINGS, SAMPLE_FILING)
    path = save_report(report, "Acme Corp")

    assert path.exists()
    assert path.suffix == ".md"
    content = path.read_text(encoding="utf-8")
    assert "Acme Corp" in content

    config.REPORTS_DIR = original


def test_assemble_report_handles_missing_swot():
    findings = {**SAMPLE_FINDINGS, "swot": None}
    report = assemble_report(findings, SAMPLE_FILING)
    assert "SWOT" in report


def test_assemble_report_handles_missing_risk_flags():
    findings = {**SAMPLE_FINDINGS, "risk_flags": []}
    report = assemble_report(findings, SAMPLE_FILING)
    assert "Risk Flags" in report


def test_assemble_report_pass_recommendation():
    findings = {**SAMPLE_FINDINGS, "investment_recommendation": "PASS"}
    report = assemble_report(findings, SAMPLE_FILING)
    assert "PASS" in report
