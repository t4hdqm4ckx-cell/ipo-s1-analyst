"""
End-to-end pipeline integration test using the sample S-1 fixture.
No API calls — uses the parser, analyzer, risk scorer, and reporter together.
"""

from pathlib import Path

from agent.analyzer import build_context_summary, extract_financial_signals
from agent.parser import S1Parser
from agent.reporter import assemble_report, report_to_dict
from agent.risk_scorer import format_risk_score, score_risk
from agent.valuation import compute_ev_revenue_multiple, extract_revenue_growth

FIXTURE = Path(__file__).parent / "fixtures" / "sample_s1_excerpt.html"


def _load_parser() -> tuple[S1Parser, dict]:
    html = FIXTURE.read_text(encoding="utf-8")
    parser = S1Parser(html, "Acme Corp")
    filing = {
        "company": "Acme Corp",
        "filing_date": "2025-03-01",
        "url": "https://sec.gov/...",
        "char_count": len(html),
    }
    return parser, filing


def test_full_pre_scan_pipeline():
    """Ensure all pre-scan modules run without error on the fixture."""
    parser, filing = _load_parser()

    # Parser
    sections = parser.list_sections()
    assert len(sections) > 0

    # Financial signals
    signals = extract_financial_signals(parser)
    assert "dollar_amounts_found" in signals

    # Context summary
    summary = build_context_summary(parser, filing)
    assert "Acme Corp" in summary

    # Risk scorer
    risk = score_risk(parser)
    assert risk["total_score"] >= 0
    assert risk["rating"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")

    risk_text = format_risk_score(risk)
    assert "Risk Score" in risk_text


def test_valuation_helpers_on_fixture():
    parser, _ = _load_parser()
    mda = parser.get_section("mda")
    growth = extract_revenue_growth(mda)
    # Fixture has "Revenue increased 67%"
    assert growth == 67.0

    # Rough EV/Revenue: implied $3.75B EV at $312.4M rev
    multiple = compute_ev_revenue_multiple(3750, 312.4)
    assert multiple == 12.0


def test_report_assembly_pipeline():
    """Simulate what happens after Claude returns findings and we assemble the report."""
    _, filing = _load_parser()

    findings = {
        "company_name": "Acme Corp",
        "filing_date": "2025-03-01",
        "executive_summary": "Acme Corp is a high-growth SaaS company.",
        "business_overview": "Cloud-based enterprise platform.",
        "products_and_services": "AcmeCloud SaaS suite.",
        "revenue_model": "Subscription + services.",
        "financial_analysis": "Revenue $312.4M, +67% YoY. Net loss $142.3M.",
        "key_metrics": "ARR $320M, NDR 128%.",
        "valuation": "12x EV/Revenue. Reasonable for 67% growth.",
        "comparable_companies": "Snowflake 18x, Palantir 10x.",
        "competitive_landscape": "SAP, Oracle (legacy), Snowflake (cloud).",
        "moat_analysis": "High switching costs, 128% NDR.",
        "swot": {
            "strengths": ["67% growth", "74% gross margin"],
            "weaknesses": ["$142M net loss"],
            "opportunities": ["International expansion"],
            "threats": ["Hyperscaler competition"],
        },
        "funding_history": "$680M raised across 5 rounds.",
        "key_investors": "Accel, Sequoia, General Atlantic.",
        "use_of_proceeds": "$200M R&D, $150M S&M.",
        "cap_table_summary": "CEO 8.2%, top 3 VCs 36.6%.",
        "risk_flags": ["$142M net loss, no profitability timeline."],
        "management_assessment": "Experienced team, CEO ex-2 prior SaaS companies.",
        "bull_case": "Growth accelerates, international launch drives upside.",
        "base_case": "45% growth, stock flat to +30% in 2 years.",
        "bear_case": "Enterprise slowdown, multiple compression.",
        "investment_recommendation": "BUY",
        "recommendation_rationale": (
            "For moderate-high risk appetite: compelling growth + unit economics. BUY."
        ),
        "key_catalysts": ["International launch", "AI feature release"],
        "key_risks_to_thesis": ["Enterprise freeze", "Hyperscaler bundling"],
        "_model": "claude-sonnet-4-6",
        "_risk_score": 18,
        "_risk_rating": "MEDIUM",
    }

    report = assemble_report(findings, filing)

    # Structural checks
    assert "# IPO S-1 Analysis: Acme Corp" in report
    assert "🟢 **BUY**" in report
    assert "🟡" in report  # MEDIUM risk badge
    assert "Executive Summary" in report
    assert "Investment Conclusion" in report
    assert "Bull Case" in report

    # Content checks
    assert "67%" in report
    assert "Accel" in report
    assert "BUY" in report

    # report_to_dict
    d = report_to_dict(findings, filing)
    assert d["recommendation"] == "BUY"
    assert d["risk_score"] == 18
    assert d["risk_rating"] == "MEDIUM"


def test_search_text_pipeline():
    parser, _ = _load_parser()
    snippets = parser.search_text("competition", context_chars=200)
    assert isinstance(snippets, list)


def test_word_count_nonzero():
    parser, _ = _load_parser()
    count = parser.word_count()
    assert count > 50
