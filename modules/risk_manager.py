"""
Risk Management Module
Implements:
  1. Macro Risk Score (1-100)
  2. Sensitivity Analysis (Beta): Impact = Price_Change × S
  3. Real Profit: Nominal_Profit × (1 - Inflation_Rate)
"""

from schemas.user_profile import get_sensitivity, UNFAVORABLE_DIRECTION


def compute_risk_score(market_data: dict, user_profile: dict) -> dict:
    industry = user_profile.get("company", {}).get("industry", "unknown")
    S = get_sensitivity(industry)

    overrides = user_profile.get("risk_config", {}).get("sensitivity_overrides")
    if overrides:
        S.update(overrides)

    assets_map = {
        "oil": "crude_oil",
        "gold": "gold",
        "btc": "bitcoin",
        "inflation": "inflation",
    }

    impacts = {}
    total_impact = 0.0

    baseline_prices = {
        "oil": 75.0,
        "gold": 2000.0,
        "btc": 60000.0,
        "inflation": 3.0,
    }

    for asset_key, market_key in assets_map.items():
        current = market_data.get(market_key, {})
        price = current.get("price") or current.get("rate") or 0
        baseline = baseline_prices.get(asset_key, 1)

        change_pct = ((price - baseline) / baseline) * 100 if baseline else 0
        sensitivity = S.get(asset_key, 0.2)

        impact = abs(change_pct) * sensitivity

        direction = "up" if change_pct >= 0 else "down"
        unfavorable = UNFAVORABLE_DIRECTION.get(asset_key)
        if direction == unfavorable:
            impact *= 1.5

        impacts[asset_key] = {
            "change_pct": round(change_pct, 2),
            "sensitivity": sensitivity,
            "impact": round(impact, 4),
            "direction": direction,
            "is_unfavorable": direction == unfavorable,
        }
        total_impact += impact

    raw_score = min(100, max(1, total_impact * 10))
    score = round(raw_score, 0)

    severity = "low"
    if score > 65:
        severity = "critical"
    elif score > 45:
        severity = "high"
    elif score > 25:
        severity = "medium"

    return {
        "macro_risk_score": int(score),
        "severity": severity,
        "total_impact": round(total_impact, 4),
        "asset_impacts": impacts,
    }


def sensitivity_impact(change_pct: float, sensitivity: float) -> float:
    return round(change_pct * sensitivity, 4)


def real_profit(nominal_profit: float, inflation_rate: float) -> dict:
    real = nominal_profit * (1 - inflation_rate / 100)
    return {
        "nominal_profit": round(nominal_profit, 2),
        "inflation_rate": inflation_rate,
        "real_profit": round(real, 2),
        "purchasing_power_loss_pct": round(inflation_rate, 2),
    }


def purchasing_power_loss(product_cost: float, inflation_rate: float) -> dict:
    real_value = product_cost / (1 + inflation_rate / 100)
    lost_amount = product_cost - real_value
    loss_pct = (1 - 1 / (1 + inflation_rate / 100)) * 100
    return {
        "product_cost": round(product_cost, 2),
        "inflation_rate": inflation_rate,
        "real_value": round(real_value, 2),
        "lost_amount": round(lost_amount, 2),
        "loss_percentage": round(loss_pct, 2),
        "break_even_revenue_needed": round(product_cost * (1 + inflation_rate / 100), 2),
    }
