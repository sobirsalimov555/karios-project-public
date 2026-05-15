import math
from typing import List


def pearson_correlation(x: List[float], y: List[float]) -> float:
    n = len(x)
    if n < 3:
        return 0.0
    mean_x = sum(x) / n
    mean_y = sum(y) / n
    num = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))
    den = math.sqrt(sum((x[i] - mean_x) ** 2 for i in range(n))) * math.sqrt(sum((y[i] - mean_y) ** 2 for i in range(n)))
    return num / den if den != 0 else 0.0


SYNTHETIC_PRICE_HISTORY = {
    "btc": [64320, 63800, 65100, 64700, 66200, 65800, 67000, 66500, 67200, 68100, 69000, 68500, 67800, 67100, 66500, 65900, 65200, 64800, 64400, 64000],
    "gold": [2335, 2340, 2338, 2345, 2350, 2348, 2355, 2360, 2358, 2370, 2365, 2360, 2355, 2348, 2342, 2338, 2330, 2325, 2320, 2318],
}


def compute_divergence_alerts(btc_prices: list = None, gold_prices: list = None) -> list:
    btc_p = btc_prices or SYNTHETIC_PRICE_HISTORY["btc"]
    gold_p = gold_prices or SYNTHETIC_PRICE_HISTORY["gold"]

    n = min(len(btc_p), len(gold_p), 30)
    if n < 5:
        return []

    btc_recent = btc_p[-n:]
    gold_recent = gold_p[-n:]

    corr = pearson_correlation(btc_recent, gold_recent)

    alerts = []

    if corr < -0.6:
        alerts.append({
            "type": "CRITICAL_DIVERGENCE",
            "correlation": round(corr, 3),
            "message": "BTC and Gold are strongly diverging. Capital rotation in progress — review portfolio hedge allocation.",
            "severity": "critical",
        })
    elif corr < -0.3:
        alerts.append({
            "type": "BEARISH_DIVERGENCE",
            "correlation": round(corr, 3),
            "message": "BTC and Gold moving in opposite directions. Potential market regime shift — monitor closely.",
            "severity": "high",
        })

    btc_recent_change = (btc_p[-1] - btc_p[0]) / btc_p[0] * 100
    gold_recent_change = (gold_p[-1] - gold_p[0]) / gold_p[0] * 100

    if btc_recent_change < -5 and gold_recent_change > 2:
        alerts.append({
            "type": "CAPITAL_FLIGHT_ALERT",
            "correlation": round(corr, 3),
            "message": f"BTC dropped {abs(btc_recent_change):.1f}% while Gold rose {gold_recent_change:.1f}%. Capital flight to safe havens detected.",
            "severity": "critical",
        })

    if not alerts:
        alerts.append({
            "type": "NORMAL",
            "correlation": round(corr, 3),
            "message": "BTC-Gold correlation within normal range.",
            "severity": "low",
        })

    return alerts
