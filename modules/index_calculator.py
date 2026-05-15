MOCK_INDEXES = {
    "sp500": {"name": "S&P 500", "value": 5642, "change_pct": 0.42, "pe_ratio": 22.5, "earnings": 250.76},
    "nasdaq": {"name": "NASDAQ Composite", "value": 18500, "change_pct": 0.85, "pe_ratio": 28.3},
    "dow": {"name": "Dow Jones Industrial Average", "value": 39850, "change_pct": -0.12, "pe_ratio": 20.1},
    "vix": {"name": "CBOE Volatility Index (VIX)", "value": 14.2, "change_pct": -3.1},
    "dxy": {"name": "US Dollar Index (DXY)", "value": 104.50, "change_pct": 0.18},
    "tnx": {"name": "10-Year Treasury Yield", "value": 4.32, "change_pct": 0.02},
    "bdi": {"name": "Baltic Dry Index", "value": 1850, "change_pct": -2.4},
    "wti": {"name": "WTI Crude Oil", "value": 78.50, "change_pct": 0.6},
}


def real_interest_rate(treasury_10y: float, inflation_rate: float) -> dict:
    real = treasury_10y - inflation_rate
    return {
        "formula": "Real Interest Rate = 10Y Treasury Yield - Inflation Rate (CPI)",
        "inputs": {"treasury_10y_pct": treasury_10y, "inflation_pct": inflation_rate},
        "result_pct": round(real, 2),
        "verdict": "Positive - bonds beating inflation" if real > 0 else "Negative - bonds losing to inflation",
        "status": "healthy" if real > 0 else "warning",
    }


def equity_risk_premium(sp500_pe: float, bond_10y_yield: float) -> dict:
    earnings_yield = (1 / sp500_pe) * 100
    erp = earnings_yield - bond_10y_yield
    return {
        "formula": "ERP = (1 / P/E × 100) - 10Y Treasury Yield",
        "inputs": {"pe_ratio": sp500_pe, "earnings_yield_pct": round(earnings_yield, 2), "bond_yield_pct": bond_10y_yield},
        "result_pct": round(erp, 2),
        "verdict": "Stocks favored over bonds" if erp > 0 else "Bonds favored over stocks",
        "status": "bullish" if erp > 1 else "neutral" if erp > 0 else "bearish",
    }


def inflation_adjusted_index(index_value: float, inflation_rate: float, years: int = 1) -> dict:
    real_value = index_value / ((1 + inflation_rate / 100) ** years)
    lost = index_value - real_value
    return {
        "formula": "Real Value = Index Value / (1 + Inflation Rate)^Years",
        "inputs": {"index_value": index_value, "inflation_pct": inflation_rate, "years": years},
        "nominal": round(index_value, 2),
        "real_value": round(real_value, 2),
        "value_eroded": round(lost, 2),
        "erosion_pct": round(lost / index_value * 100, 2),
    }


def sp500_fair_value_fed_model(trailing_earnings: float, bond_10y_yield: float) -> dict:
    fair_value = (trailing_earnings * 100) / (bond_10y_yield / 100)
    return {
        "formula": "S&P Fair Value (Fed Model) = (Trailing Earnings × 100) / 10Y Yield",
        "inputs": {"trailing_earnings": trailing_earnings, "bond_yield_decimal": bond_10y_yield / 100},
        "fair_value": round(fair_value, 2),
    }


def vix_market_stress(vix_value: float) -> dict:
    baseline = 15
    stress = ((vix_value - baseline) / baseline) * 100
    if vix_value < 15:
        level = "low"
        message = "Markets calm. Low hedging demand."
    elif vix_value < 25:
        level = "moderate"
        message = "Moderate uncertainty. Normal trading range."
    elif vix_value < 35:
        level = "high"
        message = "Elevated fear. Consider portfolio protection."
    else:
        level = "extreme"
        message = "Extreme fear / panic. Major drawdown risk."
    return {
        "formula": "VIX Stress = (Current VIX - 15) / 15 × 100",
        "vix": vix_value,
        "stress_index": round(stress, 1),
        "stress_level": level,
        "message": message,
    }


def purchasing_power_decay(amount: float, inflation_rate: float, years: int) -> dict:
    future_real = amount / ((1 + inflation_rate / 100) ** years)
    total_lost = amount - future_real
    annual = []
    for y in range(1, years + 1):
        yr_real = amount / ((1 + inflation_rate / 100) ** y)
        annual.append({"year": y, "real_value": round(yr_real, 2), "lost": round(amount - yr_real, 2)})
    return {
        "formula": "Future Real Value = Amount / (1 + Inflation Rate)^Years",
        "inputs": {"amount": amount, "inflation_pct": inflation_rate, "years": years},
        "future_real_value": round(future_real, 2),
        "total_purchasing_power_lost": round(total_lost, 2),
        "loss_pct": round(total_lost / amount * 100, 2),
        "annual_breakdown": annual,
    }


def gdp_nowcast(consumption: float, investment: float, gov_spending: float, exports: float, imports: float) -> dict:
    gdp = consumption + investment + gov_spending + (exports - imports)
    return {
        "formula": "GDP = C + I + G + (X - M)",
        "components": {
            "consumption_C": consumption,
            "investment_I": investment,
            "gov_spending_G": gov_spending,
            "exports_X": exports,
            "imports_M": imports,
            "net_exports_X_minus_M": exports - imports,
        },
        "gdp": round(gdp, 2),
    }


def format_index_change(val: float) -> str:
    return f"{'+' if val >= 0 else ''}{val:.2f}%"
