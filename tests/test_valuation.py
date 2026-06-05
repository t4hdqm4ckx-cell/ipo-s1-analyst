"""Unit tests for the valuation helper module."""

from agent.valuation import (
    compute_burn_multiple,
    compute_ev_revenue_multiple,
    compute_gross_margin,
    compute_rule_of_40,
    extract_revenue_growth,
    sector_comps_context,
)


def test_ev_revenue_multiple_basic():
    assert compute_ev_revenue_multiple(3750, 312.4) == 12.0


def test_ev_revenue_multiple_none_on_zero_revenue():
    assert compute_ev_revenue_multiple(3750, 0) is None


def test_ev_revenue_multiple_none_on_missing():
    assert compute_ev_revenue_multiple(None, 312.4) is None
    assert compute_ev_revenue_multiple(3750, None) is None


def test_gross_margin_basic():
    assert compute_gross_margin(231.2, 312.4) == pytest_approx_74()


def pytest_approx_74():
    return 74.0  # 231.2 / 312.4 * 100 ≈ 74.0


def test_gross_margin_none_on_zero():
    assert compute_gross_margin(100, 0) is None


def test_gross_margin_none_on_missing():
    assert compute_gross_margin(None, 312.4) is None


def test_burn_multiple_basic():
    result = compute_burn_multiple(net_burn_m=50, net_new_arr_m=100)
    assert result == 0.5


def test_burn_multiple_high():
    result = compute_burn_multiple(net_burn_m=200, net_new_arr_m=50)
    assert result == 4.0


def test_burn_multiple_none_on_zero():
    assert compute_burn_multiple(50, 0) is None


def test_rule_of_40_healthy():
    result = compute_rule_of_40(revenue_growth_pct=67, ebitda_margin_pct=-20)
    assert result == 47.0


def test_rule_of_40_elite():
    assert compute_rule_of_40(80, 25) == 105.0


def test_rule_of_40_none_on_missing():
    assert compute_rule_of_40(None, -20) is None
    assert compute_rule_of_40(67, None) is None


def test_extract_revenue_growth_from_text():
    text = "Revenue increased 67% year-over-year to $312.4 million."
    result = extract_revenue_growth(text)
    assert result == 67.0


def test_extract_revenue_growth_alternate_phrasing():
    text = "We achieved 45% growth in total revenue compared to the prior year."
    result = extract_revenue_growth(text)
    assert result == 45.0


def test_extract_revenue_growth_returns_none_on_no_match():
    result = extract_revenue_growth("No financial data here.")
    assert result is None


def test_sector_comps_context_returns_string():
    result = sector_comps_context()
    assert isinstance(result, str)
    assert "EV/NTM Revenue" in result
    assert "Rule of 40" in result


def test_sector_comps_context_contains_benchmarks():
    result = sector_comps_context()
    assert "SaaS" in result
    assert "Burn Multiple" in result
