import time
import json
from datetime import datetime
from urllib.request import urlopen, Request
from urllib.error import URLError

_cache = {"data": {}, "timestamp": 0}

FALLBACK = {
    "btc": {"price": 79669, "change_24h": -1.67},
    "gold": {"price": 2335},
    "oil": {"price": 78.50},
    "inflation": {"rate": 3.4},
}


def _cached(key, ttl=300):
    if key in _cache["data"] and time.time() - _cache["timestamp"] < ttl:
        return _cache["data"][key]
    return None


def _set_cache(key, value):
    _cache["data"][key] = value
    _cache["timestamp"] = time.time()


def _fetch_json(url, headers=None):
    try:
        req = Request(url, headers=headers or {}, method="GET")
        with urlopen(req, timeout=5) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None


async def get_btc():
    c = _cached("btc")
    if c: return c
    try:
        data = _fetch_json(
            "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd&include_24hr_change=true"
        )
        if data and "bitcoin" in data:
            d = data["bitcoin"]
            result = {"price": d["usd"], "change_24h": d.get("usd_24h_change", 0),
                      "timestamp": datetime.utcnow().isoformat(), "live": True}
        else:
            raise ValueError("no data")
    except Exception:
        result = {"price": FALLBACK["btc"]["price"], "change_24h": FALLBACK["btc"]["change_24h"],
                  "timestamp": datetime.utcnow().isoformat(), "live": False}
    _set_cache("btc", result)
    return result


async def get_gold():
    c = _cached("gold")
    if c: return c
    try:
        data = _fetch_json("https://api.metals.live/v1/spot/gold")
        if data and isinstance(data, list) and len(data) > 0:
            price = data[0].get("price", 0)
            result = {"price": price, "timestamp": datetime.utcnow().isoformat(), "live": True}
        else:
            raise ValueError("no data")
    except Exception:
        result = {"price": FALLBACK["gold"]["price"],
                  "timestamp": datetime.utcnow().isoformat(), "live": False}
    _set_cache("gold", result)
    return result


async def get_oil():
    c = _cached("oil")
    if c: return c
    try:
        data = _fetch_json(
            "https://api.api-ninjas.com/v1/crudeoilprice",
            headers={"X-Api-Key": "demo"}
        )
        if data and "price" in data:
            result = {"price": data["price"], "timestamp": datetime.utcnow().isoformat(), "live": True}
        else:
            raise ValueError("no data")
    except Exception:
        result = {"price": FALLBACK["oil"]["price"],
                  "timestamp": datetime.utcnow().isoformat(), "live": False}
    _set_cache("oil", result)
    return result


async def get_cpi():
    c = _cached("cpi")
    if c: return c
    try:
        data = _fetch_json(
            "https://api.api-ninjas.com/v1/inflation",
            headers={"X-Api-Key": "demo"}
        )
        if data:
            rate = data[0]["yearly_inflation_pct"] if isinstance(data, list) else data.get("yearly_inflation_pct", 0)
            result = {"rate": rate, "timestamp": datetime.utcnow().isoformat(), "live": True}
        else:
            raise ValueError("no data")
    except Exception:
        result = {"rate": FALLBACK["inflation"]["rate"],
                  "timestamp": datetime.utcnow().isoformat(), "live": False}
    _set_cache("cpi", result)
    return result


async def fetch_market():
    import asyncio
    btc, gold, oil, cpi = await asyncio.gather(get_btc(), get_gold(), get_oil(), get_cpi())
    return {
        "bitcoin": btc,
        "gold": gold,
        "crude_oil": oil,
        "inflation": cpi,
        "updated_at": datetime.utcnow().isoformat(),
    }
