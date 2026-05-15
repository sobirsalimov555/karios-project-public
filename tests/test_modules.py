"""Unit tests for all macro finance modules."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from schemas.user_profile import get_sensitivity, default_user_profile
from modules.risk_manager import compute_risk_score, real_profit, sensitivity_impact
from modules.hedging_advisor import hedging_advisor
from modules.monte_carlo import monte_carlo_var
from modules.cash_flow import forecast_cash_flow
from modules.correlation_analyzer import compute_divergence_alerts, pearson_correlation

MOCK_MARKET = {
    "bitcoin": {"price": 64320, "change_24h": -2.3},
    "gold": {"price": 2335},
    "crude_oil": {"price": 78.50},
    "inflation": {"rate": 3.4},
}

PROFILE = default_user_profile()


def test_get_sensitivity():
    s = get_sensitivity("logistics")
    assert s["oil"] == 0.80
    assert s["btc"] == 0.05

    s2 = get_sensitivity("unknown")
    assert s2["oil"] == 0.30


def test_risk_score_returns_valid_range():
    result = compute_risk_score(MOCK_MARKET, PROFILE)
    assert 1 <= result["macro_risk_score"] <= 100
    assert result["severity"] in ("low", "medium", "high", "critical")
    assert "asset_impacts" in result
    assert "oil" in result["asset_impacts"]
    assert "btc" in result["asset_impacts"]


def test_sensitivity_impact():
    impact = sensitivity_impact(10.0, 0.8)
    assert impact == 8.0
    impact2 = sensitivity_impact(5.0, 0.1)
    assert impact2 == 0.5


def test_real_profit():
    result = real_profit(1_000_000, 4.0)
    assert result["real_profit"] == 960_000.0
    assert result["purchasing_power_loss_pct"] == 4.0


def test_hedging_advisor_below_threshold():
    result = hedging_advisor(MOCK_MARKET, PROFILE)
    assert "recommendation" in result


def test_hedging_advisor_above_threshold():
    high_inflation_market = dict(MOCK_MARKET)
    high_inflation_market["inflation"] = {"rate": 7.0}
    result = hedging_advisor(high_inflation_market, PROFILE)
    assert len(result["details"]) > 0
    assert result["total_hedge_pct"] > 0


def test_monte_carlo_var():
    result = monte_carlo_var(MOCK_MARKET, PROFILE, scenarios=100)
    assert "var_95_pct" in result
    assert "var_99_pct" in result
    assert result["num_scenarios"] == 100


def test_cash_flow_forecast():
    result = forecast_cash_flow(MOCK_MARKET, PROFILE, months=6)
    assert len(result["forecast"]) == 6
    assert result["runway_months"] >= 0
    assert result["inputs"]["current_monthly_burn"] == 600_000


def test_divergence_alerts():
    btc_high = [60000 + i * 200 for i in range(20)]
    gold_stable = [2300] * 20
    alerts = compute_divergence_alerts(btc_high, gold_stable)
    assert len(alerts) >= 1
    assert alerts[0]["type"] in ("NORMAL", "BEARISH_DIVERGENCE", "CRITICAL_DIVERGENCE", "CAPITAL_FLIGHT_ALERT")


def test_pearson_correlation():
    x = [1, 2, 3, 4, 5]
    y = [2, 4, 6, 8, 10]
    assert abs(pearson_correlation(x, y) - 1.0) < 0.001

    y_neg = [-2, -4, -6, -8, -10]
    assert abs(pearson_correlation(x, y_neg) - (-1.0)) < 0.001


if __name__ == "__main__":
    test_get_sensitivity()
    test_risk_score_returns_valid_range()
    test_sensitivity_impact()
    test_real_profit()
    test_hedging_advisor_below_threshold()
    test_hedging_advisor_above_threshold()
    test_monte_carlo_var()
    test_cash_flow_forecast()
    test_divergence_alerts()
    test_pearson_correlation()
    print("All tests passed.")
