"""
Monte Carlo VaR Simulation
Runs N scenarios of BTC/Oil price paths over 1 quarter to compute Value at Risk.
"""

import random
import math
from typing import Dict, List

HISTORICAL_DATA = {
    "btc": {"mean": 0.0012, "std": 0.035},
    "oil": {"mean": 0.0003, "std": 0.022},
    "gold": {"mean": 0.0004, "std": 0.012},
}

TRADING_DAYS_QUARTER = 63


def run_scenario(price_start: float, asset: str, days: int) -> list:
    params = HISTORICAL_DATA.get(asset, {"mean": 0.0, "std": 0.02})
    prices = [price_start]
    for _ in range(days):
        r = random.gauss(params["mean"], params["std"])
        prices.append(prices[-1] * (1 + r))
    return prices


def monte_carlo_var(
    market_data: dict,
    user_profile: dict,
    scenarios: int = 1000,
    confidence: float = 0.95,
) -> dict:
    btc_price = market_data.get("bitcoin", {}).get("price", 60000)
    oil_price = market_data.get("crude_oil", {}).get("price", 75)
    gold_price = market_data.get("gold", {}).get("price", 2000)

    exposure = user_profile.get("financials", {}).get("asset_exposure", {})
    btc_holdings = exposure.get("btc_holdings_usd", 0)
    oil_exposure_pct = user_profile.get("financials", {}).get("expense_breakdown", {}).get("fuel_energy_pct", 0)

    btc_qty = btc_holdings / btc_price if btc_price else 0
    oil_sensitivity = oil_exposure_pct * 100_000

    results = []

    for _ in range(scenarios):
        btc_path = run_scenario(btc_price, "btc", TRADING_DAYS_QUARTER)
        oil_path = run_scenario(oil_price, "oil", TRADING_DAYS_QUARTER)
        gold_path = run_scenario(gold_price, "gold", TRADING_DAYS_QUARTER)

        btc_final = btc_qty * btc_path[-1]
        oil_impact = oil_sensitivity * (oil_path[-1] - oil_price) / oil_price
        gold_final = exposure.get("gold_holdings_usd", 0) * gold_path[-1] / gold_price

        initial_portfolio = btc_holdings + exposure.get("gold_holdings_usd", 0)
        final_portfolio = btc_final + gold_final
        pnl = final_portfolio - initial_portfolio - oil_impact

        results.append(pnl / max(initial_portfolio, 1) * 100 if initial_portfolio else 0)

    results.sort()
    var_idx_95 = max(0, int(scenarios * (1 - confidence)))
    var_idx_99 = max(0, int(scenarios * 0.01))

    var_95 = round(results[var_idx_95], 2)
    var_99 = round(results[var_idx_99], 2)

    positive_count = sum(1 for r in results if r > 0)
    upside_prob = round(positive_count / scenarios * 100, 1)

    return {
        "var_95_pct": var_95,
        "var_99_pct": var_99,
        "var_95_label": f"5% chance of losing >{abs(var_95)}%",
        "var_99_label": f"1% chance of losing >{abs(var_99)}%",
        "upside_probability_pct": upside_prob,
        "num_scenarios": scenarios,
        "horizon_days": TRADING_DAYS_QUARTER,
        "worst_case_pct": round(results[0], 2),
        "best_case_pct": round(results[-1], 2),
        "median_pct": round(results[scenarios // 2], 2),
    }
