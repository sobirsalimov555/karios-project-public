INDUSTRY_SENSITIVITIES = {
    "logistics":     {"oil": 0.80, "gold": 0.05, "btc": 0.05, "inflation": 0.60},
    "software":      {"oil": 0.10, "gold": 0.10, "btc": 0.40, "inflation": 0.30},
    "retail":        {"oil": 0.30, "gold": 0.15, "btc": 0.10, "inflation": 0.50},
    "manufacturing": {"oil": 0.50, "gold": 0.15, "btc": 0.05, "inflation": 0.55},
    "finance":       {"oil": 0.10, "gold": 0.35, "btc": 0.30, "inflation": 0.40},
    "healthcare":    {"oil": 0.20, "gold": 0.25, "btc": 0.10, "inflation": 0.45},
}

DEFAULT_SENSITIVITY = {"oil": 0.30, "gold": 0.20, "btc": 0.15, "inflation": 0.45}

UNFAVORABLE_DIRECTION = {
    "oil": "up",
    "gold": "down",
    "btc": "down",
    "inflation": "up",
}


def get_sensitivity(industry: str) -> dict:
    return INDUSTRY_SENSITIVITIES.get(industry.lower(), DEFAULT_SENSITIVITY)


def default_user_profile():
    return {
        "company": {
            "name": "Example Corp",
            "industry": "software",
            "tier": "mid",
            "revenue_annual": 10_000_000,
        },
        "financials": {
            "monthly_burn_rate": 600_000,
            "cash_reserves": 3_000_000,
            "nominal_profit_last_q": 400_000,
            "expense_breakdown": {
                "fuel_energy_pct": 0.05,
                "payroll_pct": 0.50,
                "materials_pct": 0.25,
                "other_pct": 0.20,
            },
            "asset_exposure": {
                "btc_holdings_usd": 100_000,
                "gold_holdings_usd": 50_000,
                "cash_usd": 2_000_000,
                "receivables_usd": 850_000,
            },
        },
        "risk_config": {
            "sensitivity_overrides": None,
            "var_confidence": 0.95,
            "hedge_threshold_inflation": 5.0,
        },
    }
