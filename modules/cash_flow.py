"""
Simple Cash Flow Forecast
Adjusts projected expenses based on inflation and oil prices.
"""


def forecast_cash_flow(market_data: dict, user_profile: dict, months: int = 12) -> dict:
    inflation_rate = market_data.get("inflation", {}).get("rate", 3.0)
    oil_price = market_data.get("crude_oil", {}).get("price", 75.0)

    financials = user_profile.get("financials", {})
    burn = financials.get("monthly_burn_rate", 0)
    cash = financials.get("cash_reserves", 0) or financials.get("asset_exposure", {}).get("cash_usd", 0)
    expenses = financials.get("expense_breakdown", {})

    baseline_oil = 75.0
    fuel_pct = expenses.get("fuel_energy_pct", 0.10)
    payroll_pct = expenses.get("payroll_pct", 0.35)
    materials_pct = expenses.get("materials_pct", 0.25)
    other_pct = expenses.get("other_pct", 0.20)

    oil_adjust = 1 + (oil_price - baseline_oil) / baseline_oil * fuel_pct
    inflation_adjust = 1 + (inflation_rate / 100) * (payroll_pct + materials_pct + other_pct)

    projected_burn = burn * oil_adjust * inflation_adjust

    monthly = []
    cumulative_burn = 0
    for m in range(1, months + 1):
        month_burn = projected_burn * ((1 + inflation_rate / 100 / 12) ** (m - 1))
        cumulative_burn += month_burn
        remaining_cash = cash - cumulative_burn
        monthly.append({
            "month": m,
            "projected_burn": round(month_burn, 2),
            "cumulative_burn": round(cumulative_burn, 2),
            "remaining_cash": round(remaining_cash, 2),
            "status": "solvent" if remaining_cash > 0 else "depleted",
        })

    return {
        "inputs": {
            "current_monthly_burn": burn,
            "cash_reserves": cash,
            "inflation_rate": inflation_rate,
            "oil_price": oil_price,
        },
        "adjustments": {
            "oil_adjustment_factor": round(oil_adjust, 4),
            "inflation_adjustment_factor": round(inflation_adjust, 4),
            "combined_adjustment": round(oil_adjust * inflation_adjust, 4),
            "projected_monthly_burn": round(projected_burn, 2),
        },
        "forecast": monthly,
        "runway_months": len([m for m in monthly if m["status"] == "solvent"]),
    }
