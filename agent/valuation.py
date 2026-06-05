"""
Valuation helpers — compute common IPO valuation metrics from extracted financials.
These are passed as additional context to Claude rather than replacing its reasoning.
"""

import re


def _parse_millions(text: str) -> float | None:
    """Parse a dollar string like '$312.4 million' or '$1.2B' into float millions."""
    text = text.strip().lower()
    text = text.replace(",", "").replace("$", "")

    multipliers = {
        "billion": 1_000, "b": 1_000,
        "million": 1, "m": 1,
        "thousand": 0.001, "k": 0.001,
    }
    for suffix, mult in multipliers.items():
        if text.endswith(suffix):
            try:
                return float(text[: -len(suffix)].strip()) * mult
            except ValueError:
                return None

    try:
        return float(text)
    except ValueError:
        return None


def compute_ev_revenue_multiple(
    enterprise_value_m: float | None,
    revenue_m: float | None,
) -> float | None:
    """Return EV/Revenue multiple, or None if inputs are missing."""
    if enterprise_value_m and revenue_m and revenue_m > 0:
        return round(enterprise_value_m / revenue_m, 1)
    return None


def compute_gross_margin(gross_profit_m: float | None, revenue_m: float | None) -> float | None:
    if gross_profit_m is not None and revenue_m and revenue_m > 0:
        return round(gross_profit_m / revenue_m * 100, 1)
    return None


def compute_burn_multiple(
    net_burn_m: float | None,
    net_new_arr_m: float | None,
) -> float | None:
    """Burn multiple = net cash burned / net new ARR. <1 is excellent, >2 is concerning."""
    if net_burn_m and net_new_arr_m and net_new_arr_m > 0:
        return round(abs(net_burn_m) / net_new_arr_m, 2)
    return None


def compute_rule_of_40(
    revenue_growth_pct: float | None,
    ebitda_margin_pct: float | None,
) -> float | None:
    """Rule of 40 = revenue growth % + EBITDA margin %. >40 is healthy SaaS."""
    if revenue_growth_pct is not None and ebitda_margin_pct is not None:
        return round(revenue_growth_pct + ebitda_margin_pct, 1)
    return None


def extract_revenue_growth(mda_text: str) -> float | None:
    """Attempt to extract YoY revenue growth rate from MD&A text."""
    patterns = [
        r"revenue\s+(?:increased?|grew?|rose?)\s+(\d+)%",
        r"(\d+)%\s+(?:increase?|growth)\s+in\s+(?:total\s+)?revenue",
        r"revenue\s+growth\s+of\s+(\d+)%",
    ]
    for pat in patterns:
        match = re.search(pat, mda_text, re.IGNORECASE)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                continue
    return None


def sector_comps_context(sector_hint: str = "") -> str:
    """
    Return a static reference table of recent SaaS/tech IPO valuation ranges.
    Used to give Claude context when reasoning about comps without a data API.
    """
    return """
## Reference: Recent Tech/SaaS IPO Valuation Benchmarks (2023-2025)

| Cohort | EV/NTM Revenue | EV/NTM EBITDA | NTM Rev Growth | Notes |
|---|---|---|---|---|
| High-growth SaaS (>50% growth) | 12–20x | N/A (loss-making) | 50-80% | e.g. pre-AI wave leaders |
| Mid-growth SaaS (25-50%) | 6–12x | 30–60x | 25–50% | Most common IPO range |
| Mature SaaS (<25% growth) | 3–6x | 15–25x | 10–25% | Value/profitability focused |
| Defense/Aerospace tech | 4–8x rev | 15–30x EBITDA | 10–30% | Contract-driven, stable |
| Consumer tech/marketplace | 2–6x rev | 15–40x EBITDA | 15–40% | GMV-based, take-rate critical |
| AI/ML infrastructure | 15–35x rev | N/A | 80-150% | Premium for AI exposure |

**Rule of 40 Benchmarks**
- >60: Elite (Snowflake-era, pre-rate-hike)
- 40–60: Strong, IPO-able
- 20–40: Marginal, needs clear path to improvement
- <20: Challenged, requires heavy discount to comps

**Burn Multiple Benchmarks (for pre-profitability companies)**
- <0.5: Extremely efficient
- 0.5–1.0: Good
- 1.0–2.0: Acceptable
- >2.0: Concerning, may signal structural inefficiency
""".strip()
