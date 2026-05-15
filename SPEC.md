# Karios — Technical Specification

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    API Layer (FastAPI)                    │
├────────────┬────────────┬──────────────┬────────────────┤
│ Risk       │ Hedging    │ Monte Carlo  │ Cash Flow      │
│ Module     │ Advisor    │ Simulation   │ Forecast       │
├────────────┴────────────┴──────────────┴────────────────┤
│                Business Profile Engine                    │
│  (Industry weights · Sensitivity factors · Asset exposure)│
├────────────┬────────────┬──────────────┬────────────────┤
│ BTC Fetcher│ Gold Fetch │ Oil Fetcher  │ CPI/Inflation  │
└────────────┴────────────┴──────────────┴────────────────┘
```

## 2. Data Schema — User Profile

```json
{
  "user_id": "uuid",
  "company": {
    "name": "Acme Logistics",
    "industry": "logistics",
    "tier": "mid",
    "revenue_annual": 50_000_000,
    "employees": 200
  },
  "financials": {
    "monthly_burn_rate": 3_200_000,
    "cash_reserves": 12_000_000,
    "nominal_profit_last_q": 2_100_000,
    "expense_breakdown": {
      "fuel_energy_pct": 0.25,
      "payroll_pct": 0.40,
      "materials_pct": 0.20,
      "other_pct": 0.15
    },
    "asset_exposure": {
      "btc_holdings_usd": 500_000,
      "gold_holdings_usd": 200_000,
      "cash_usd": 8_000_000,
      "receivables_usd": 3_300_000
    }
  },
  "risk_config": {
    "sensitivity_overrides": null,
    "var_confidence": 0.95,
    "hedge_threshold_inflation": 5.0
  }
}
```

## 3. Sensitivity Factors by Industry

| Industry          | S_oil | S_gold | S_btc | S_inflation |
|-------------------|-------|--------|-------|-------------|
| logistics         | 0.80  | 0.05   | 0.05  | 0.60        |
| software          | 0.10  | 0.10   | 0.40  | 0.30        |
| retail            | 0.30  | 0.15   | 0.10  | 0.50        |
| manufacturing     | 0.50  | 0.15   | 0.05  | 0.55        |
| finance           | 0.10  | 0.35   | 0.30  | 0.40        |
| healthcare        | 0.20  | 0.25   | 0.10  | 0.45        |

Default for unknown: `{ "oil": 0.3, "gold": 0.2, "btc": 0.15, "inflation": 0.45 }`

## 4. Risk Management Module

### 4.1 Macro Risk Score (1-100)

```
For each asset a in [oil, gold, btc, inflation]:
    change_pct_a = (current_price - previous_price) / previous_price * 100
    impact_a = abs(change_pct_a) * S_a

    if change_pct_a is unfavorable (e.g., oil up for logistics):
        impact_a *= 1.5  # penalty multiplier

raw_score = sum(impact_a for all a)
score = min(100, max(1, raw_score * 10))
```

### 4.2 Sensitivity Analysis (Beta)

```
Impact = Price_Change_Pct × S_asset

Example — Logistics, Oil spikes 10%:
    Impact = 10% × 0.80 = 8% expense increase
```

### 4.3 Real Profit Calculator

```
Real_Profit = Nominal_Profit × (1 - Inflation_Rate)
```

### 4.4 Asset Correlation / Divergence Alert

```
Track 30-day rolling correlation between BTC and Gold.
If correlation drops below -0.3 → BEARISH_DIVERGENCE
If correlation drops below -0.6 → CRITICAL_DIVERGENCE

Also: if BTC drops >5% AND Gold rises >2% in same window → CAPITAL_FLIGHT_ALERT
```

## 5. Hedging Advisor

```
IF inflation_rate > threshold (5%):
    IF gold_trend == "up" (30d SMA rising):
        hedge_gold_pct = min(40, inflation_rate * 6)
    IF btc_trend == "up":
        hedge_btc_pct = min(15, (inflation_rate - 3) * 5)

    recommended_hedge = {
        "gold": f"{hedge_gold_pct}% of excess cash",
        "btc": f"{hedge_btc_pct}% of excess cash",
        "reasoning": "Inflation erodes cash. Gold/BTC are non-correlated stores."
    }
```

## 6. Monte Carlo — Value at Risk (VaR)

```
Parameters:
    - assets: ["BTC", "Oil"]
    - scenarios: 1000
    - horizon: 63 trading days (1 quarter)
    - confidence: 95%

For each scenario:
    for each day in 63:
        for each asset:
            daily_return = historical_mean + historical_std * random_gaussian()
            price *= (1 + daily_return)
    
    portfolio_change = (final_value - initial_value) / initial_value
    store in results[]

Sort results ascending.
VaR_95 = results[50]    # 5th percentile
VaR_99 = results[10]    # 1st percentile

Output:
    VaR_95: "-12.4%"  (5% chance of losing >12.4%)
    VaR_99: "-18.7%"  (1% chance of losing >18.7%)
    Max_Drawdown: worst single scenario
```

## 7. Simple Cash Flow Forecast

```
Input: current_burn, inflation_rate, oil_price, expense_breakdown

fuel_adj = 1 + (oil_price - baseline_oil) / baseline_oil * fuel_pct
inflation_adj = 1 + inflation_rate * (payroll_pct + materials_pct + other_pct)

projected_burn = current_burn * fuel_adj * inflation_adj

For months 1-12:
    month_n_burn = projected_burn * (1 + inflation_rate/12)^n
    month_n_cash = cash_reserves - cumulative_burn
```

## 8. API Structure

```
GET  /api/v1/market              → { btc, gold, oil, inflation }
GET  /api/v1/risk-score          → { score: 47, breakdown: {...} }
POST /api/v1/risk-score          → body: { user_profile } → { score, breakdown }
POST /api/v1/hedging-advisor     → body: { user_profile } → { recommendations }
POST /api/v1/monte-carlo/var     → body: { user_profile } → { VaR_95, VaR_99, scenarios }
POST /api/v1/cash-flow-forecast  → body: { user_profile } → { monthly: [...] }
GET  /api/v1/alerts/divergence   → { divergences: [...] }
```

## 9. Implementation Order (Roadmap)

```
Phase 1: Dashboard
  ├── Market data fetchers (BTC, Gold, Oil, CPI)
  ├── Basic REST endpoints
  └── Static charts

Phase 2: Business Profile
  ├── User profile CRUD
  ├── Industry sensitivity table
  └── Asset exposure input

Phase 3: The Bridge (Risk Engine)
  ├── Macro Risk Score
  ├── Sensitivity Impact reports
  ├── Real Profit adjustment
  └── Correlation/Divergence alerts

Phase 4: Advanced
  ├── Monte Carlo VaR simulation
  ├── Hedging Advisor with balance sheet
  └── Cash Flow Forecaster
```
