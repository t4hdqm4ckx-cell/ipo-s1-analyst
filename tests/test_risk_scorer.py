"""Unit tests for the risk scorer module."""

from pathlib import Path

from agent.parser import S1Parser
from agent.risk_scorer import format_risk_score, score_risk

FIXTURE = Path(__file__).parent / "fixtures" / "sample_s1_excerpt.html"
HIGH_RISK_HTML = """
<html><body>
<h2>RISK FACTORS</h2>
<p>There is substantial going concern doubt about our ability to continue as a going concern.</p>
<p>We have identified a material weakness in our internal controls over financial reporting.</p>
<p>We have a history of net losses. We are unable to achieve profitability in the near term.</p>
<p>Key-man dependency: our CEO is critical to operations.</p>
<p>We have dual-class share structure. Class B shareholders have no voting rights.</p>
<p>A single customer accounts for 65% of our revenue — customer concentration risk.</p>
<p>Pending litigation in multiple jurisdictions.</p>
<p>Export control and ITAR regulations apply to our products.</p>
<p>Selling stockholders intend to sell shares in this offering.</p>
</body></html>
"""

LOW_RISK_HTML = """
<html><body>
<h2>RISK FACTORS</h2>
<p>Our business may be affected by general economic conditions.</p>
<p>We face competition from established companies.</p>
<p>Our success depends on continued market adoption of our products.</p>
</body></html>
"""


def test_score_risk_fixture():
    html = FIXTURE.read_text(encoding="utf-8")
    parser = S1Parser(html, "Acme Corp")
    result = score_risk(parser)
    assert isinstance(result["total_score"], int)
    assert result["total_score"] >= 0
    assert result["rating"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")
    assert isinstance(result["flags_triggered"], list)


def test_score_risk_high_risk_html():
    parser = S1Parser(HIGH_RISK_HTML, "HighRiskCo")
    result = score_risk(parser)
    assert result["total_score"] >= 30
    assert result["rating"] in ("HIGH", "CRITICAL")
    assert result["flags_count"] >= 5


def test_score_risk_low_risk_html():
    parser = S1Parser(LOW_RISK_HTML, "LowRiskCo")
    result = score_risk(parser)
    assert result["total_score"] < 20
    assert result["rating"] in ("LOW", "MEDIUM")


def test_going_concern_adds_highest_weight():
    parser = S1Parser(HIGH_RISK_HTML, "GCCo")
    result = score_risk(parser)
    labels = [f[0] for f in result["flags_triggered"]]
    assert any("going-concern" in lbl.lower() or "going concern" in lbl.lower() for lbl in labels)


def test_format_risk_score_returns_string():
    parser = S1Parser(HIGH_RISK_HTML, "HighRiskCo")
    result = score_risk(parser)
    text = format_risk_score(result)
    assert isinstance(text, str)
    assert "Risk Score" in text
    assert result["rating"] in text


def test_format_risk_score_low_risk():
    parser = S1Parser(LOW_RISK_HTML, "LowRiskCo")
    result = score_risk(parser)
    text = format_risk_score(result)
    assert "LOW" in text or "MEDIUM" in text


def test_score_risk_empty_doc():
    parser = S1Parser("", "EmptyCo")
    result = score_risk(parser)
    assert result["total_score"] == 0
    assert result["rating"] == "LOW"
    assert result["flags_count"] == 0
