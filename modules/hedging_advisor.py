"""
Hedging Advisor
Analyzes balance sheet + market conditions to recommend hedges.
"""


def compute_sma(prices: list, window: int = 30) -> float:
    if len(prices) < window:
        return sum(prices) / len(prices) if prices else 0
    return sum(prices[-window:]) / window


def get_trend(prices: list) -> str:
    if len(prices) < 2:
        return "neutral"
    short = compute_sma(prices, min(7, len(prices)))
    long = compute_sma(prices, len(prices))
    if short > long * 1.02:
        return "up"
    if short < long * 0.98:
        return "down"
    return "neutral"


def hedging_advisor(market_data: dict, user_profile: dict) -> dict:
    inflation = market_data.get("inflation", {})
    gold = market_data.get("gold", {})
    btc = market_data.get("bitcoin", {})

    inflation_rate = inflation.get("rate", 0)
    financials = user_profile.get("financials", {})
    cash = financials.get("cash_reserves", 0) or financials.get("asset_exposure", {}).get("cash_usd", 0)
    threshold = user_profile.get("risk_config", {}).get("hedge_threshold_inflation", 5.0)

    gold_price = gold.get("price", 0)
    btc_price = btc.get("price", 0)

    recommendations = []
    total_hedge_pct = 0

    if inflation_rate > threshold:
        if gold_price > 0:
            hedge_gold = min(40, round(inflation_rate * 6, 0))
            recommendations.append({
                "asset": "gold",
                "allocation_pct": hedge_gold,
                "amount_usd": round(cash * hedge_gold / 100, 2),
                "rationale": f"Inflation at {inflation_rate}% erodes cash. Gold is a traditional inflation hedge.",
            })
            total_hedge_pct += hedge_gold

        btc_24h = btc.get("change_24h", 0) or 0
        if btc_price > 0 and btc_24h > -5:
            hedge_btc = min(15, max(0, round((inflation_rate - 3) * 5, 0)))
            if hedge_btc > 0 and total_hedge_pct + hedge_btc <= 50:
                recommendations.append({
                    "asset": "btc",
                    "allocation_pct": hedge_btc,
                    "amount_usd": round(cash * hedge_btc / 100, 2),
                    "rationale": f"Non-correlated digital asset. Limited allocation ({hedge_btc}%) as tactical inflation hedge.",
                })
                total_hedge_pct += hedge_btc

    if not recommendations:
        return {
            "recommendation": "No hedge needed — inflation within threshold.",
            "details": [],
            "total_hedge_pct": 0,
        }

    return {
        "recommendation": f"Allocate {total_hedge_pct}% of cash reserves ({' + '.join([r['asset'] for r in recommendations])})",
        "details": recommendations,
        "total_hedge_pct": total_hedge_pct,
        "remaining_cash_usd": round(cash * (1 - total_hedge_pct / 100), 2),
    }
