"""
Risk scoring — assigns a quantitative risk score to an S-1 based on red flags
found in the filing. Purely additive: each flag found adds weight.
"""

import re

from agent.parser import S1Parser

# Each entry: (pattern, weight, label)
# Weight is the risk contribution (higher = riskier). Max realistic score ~100.
RISK_SIGNALS: list[tuple[str, int, str]] = [
    # ── Existential / financial health ──────────────────────────────────────
    (r"going[- ]concern", 20, "Going-concern doubt raised by auditors"),
    (r"material\s+weakness", 15, "Material weakness in internal controls"),
    (r"significant\s+doubt", 10, "Significant doubt language in financials"),
    (r"unable\s+to\s+achieve\s+profitab", 8, "No clear path to profitability stated"),
    (r"history\s+of\s+net\s+loss", 5, "History of net losses disclosed"),
    # ── Concentration risks ─────────────────────────────────────────────────
    (r"customer\s+concentration|single\s+customer", 8, "Customer concentration risk"),
    (r"revenue\s+concentration|geographic\s+concentration", 5, "Revenue/geographic concentration"),
    (r"supplier\s+concentration|sole\s+source", 6, "Supplier or sole-source dependency"),
    # ── Governance ──────────────────────────────────────────────────────────
    (r"dual[- ]class|class\s+[ab]\s+common", 6, "Dual-class share structure (reduced investor control)"),
    (r"no\s+voting\s+rights|limited\s+voting", 5, "Limited or no voting rights for new investors"),
    (r"anti[- ]takeover", 4, "Anti-takeover provisions"),
    # ── Regulatory / legal ──────────────────────────────────────────────────
    (r"export\s+control|itar|ear\s+compliance", 7, "Export control / ITAR regulatory exposure"),
    (r"government\s+contract|federal\s+contract", 4, "Government contract dependency"),
    (r"pending\s+litigation|material\s+litigation", 6, "Material pending litigation"),
    (r"regulatory\s+approval\s+required|fda\s+approval", 7, "Regulatory approval required for core product"),
    (r"privacy\s+regulation|gdpr|ccpa", 3, "Data privacy regulatory exposure"),
    # ── Operational ─────────────────────────────────────────────────────────
    (r"key\s*[- ]?man|key\s+personnel", 5, "Key-person dependency risk"),
    (r"cybersecurity\s+incident|data\s+breach", 4, "Prior cybersecurity incident disclosed"),
    (r"reliance\s+on\s+third\s+part|third[- ]party\s+provider", 3, "Heavy third-party dependency"),
    # ── Insider dynamics ────────────────────────────────────────────────────
    (r"selling\s+stockholder|selling\s+shareholder", 5, "Insiders selling shares in IPO"),
    (r"related[- ]party\s+transaction", 3, "Related-party transactions disclosed"),
]


def score_risk(parser: S1Parser) -> dict:
    """
    Scan the filing and return a risk score dict with:
      - total_score: 0–100+ (higher = riskier)
      - rating: LOW / MEDIUM / HIGH / CRITICAL
      - flags_triggered: list of (label, weight) tuples
    """
    risk_text = parser.get_section("risk_factors")
    full_text = parser.get_section("full")
    combined = f"{risk_text}\n\n{full_text}"

    flags_triggered: list[tuple[str, int]] = []
    total_score = 0

    for pattern, weight, label in RISK_SIGNALS:
        if re.search(pattern, combined, re.IGNORECASE):
            flags_triggered.append((label, weight))
            total_score += weight

    if total_score < 15:
        rating = "LOW"
    elif total_score < 30:
        rating = "MEDIUM"
    elif total_score < 50:
        rating = "HIGH"
    else:
        rating = "CRITICAL"

    return {
        "total_score": total_score,
        "rating": rating,
        "flags_triggered": flags_triggered,
        "flags_count": len(flags_triggered),
    }


def format_risk_score(risk_result: dict) -> str:
    """Return a formatted risk score summary for inclusion in the agent context."""
    lines = [
        f"## Automated Risk Score: {risk_result['total_score']}/100 — {risk_result['rating']}",
        f"({risk_result['flags_count']} risk signals detected)\n",
    ]
    if risk_result["flags_triggered"]:
        lines.append("| Signal | Weight |")
        lines.append("|---|---|")
        for label, weight in sorted(risk_result["flags_triggered"], key=lambda x: -x[1]):
            lines.append(f"| {label} | +{weight} |")
    else:
        lines.append("_No automated risk signals detected._")
    return "\n".join(lines)
