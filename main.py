import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from jinja2 import Environment, FileSystemLoader

from schemas.user_profile import default_user_profile, get_sensitivity
from modules.risk_manager import compute_risk_score, real_profit, purchasing_power_loss
from modules.hedging_advisor import hedging_advisor
from modules.monte_carlo import monte_carlo_var
from modules.cash_flow import forecast_cash_flow
from modules.correlation_analyzer import compute_divergence_alerts
from modules.index_calculator import (
    MOCK_INDEXES, real_interest_rate, equity_risk_premium,
    inflation_adjusted_index, sp500_fair_value_fed_model,
    vix_market_stress, purchasing_power_decay,
)
from modules.auth import (
    signup, login, logout as auth_logout, get_user_by_token,
    save_profile as auth_save_profile, load_profile as auth_load_profile,
    save_income_record, load_income_records,
)
from modules.auth import SUPABASE_URL as _SUPABASE_URL, SUPABASE_KEY as _SUPABASE_KEY
_supabase_mode = bool(_SUPABASE_URL and _SUPABASE_KEY)
from data.market_data import fetch_market

from starlette.responses import RedirectResponse
import json

app = FastAPI(title="Karios", version="2.0.0")

MarketCache = {}  # populated at startup

_tpl_dir = os.path.join(os.path.dirname(__file__), "templates")
_jinja_env = Environment(loader=FileSystemLoader(_tpl_dir))
static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

LIVE_MARKET = {
    "bitcoin": {"price": 79669, "change_24h": -1.67, "live": False},
    "gold": {"price": 2335, "live": False},
    "crude_oil": {"price": 78.50, "live": False},
    "inflation": {"rate": 3.4, "live": False},
}


class UserProfileRequest(BaseModel):
    user_profile: dict = Field(default_factory=default_user_profile)

# --- In-memory profile (stateless fallback = default, POST /profile to set) ---
ACTIVE_PROFILE = dict(default_user_profile())


def _profile() -> dict:
    return dict(ACTIVE_PROFILE)


# --- PAGE ---

async def _get_user(request: Request):
    token = request.cookies.get("session_token", "")
    return await get_user_by_token(token) if token else None


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, industry: str = ""):
    profile = _profile()
    if industry:
        profile["company"]["industry"] = industry
        ACTIVE_PROFILE["company"]["industry"] = industry
    user = await _get_user(request)
    try:
        fresh = await fetch_market()
        LIVE_MARKET.update(fresh)
    except Exception:
        pass
    market = LIVE_MARKET
    risk = compute_risk_score(market, profile)
    alerts = hedging_advisor(market, profile)
    divergence = compute_divergence_alerts()
    fin = profile.get("financials", {})
    nominal = fin.get("nominal_profit_last_q", 500000)
    rp = real_profit(nominal, market["inflation"]["rate"])
    html = _jinja_env.get_template("dashboard.html").render(
        market=market, risk=risk, alerts=alerts, divergence=divergence,
        industry=profile["company"]["industry"],
        sensitivities=get_sensitivity(profile["company"]["industry"]),
        real_profit_result=rp, profile=profile, user=user,
    )
    return HTMLResponse(html)


@app.get("/risk-breakdown", response_class=HTMLResponse)
async def risk_breakdown(request: Request, industry: str = ""):
    profile = _profile()
    if industry:
        profile["company"]["industry"] = industry
    user = await _get_user(request)
    market = LIVE_MARKET
    risk = compute_risk_score(market, profile)
    divergence = compute_divergence_alerts()
    html = _jinja_env.get_template("risk_breakdown.html").render(
        risk=risk, divergence=divergence, industry=profile["company"]["industry"], user=user,
    )
    return HTMLResponse(html)


@app.get("/purchasing-power", response_class=HTMLResponse)
async def purchasing_power_page(request: Request, cost: float = 0, profit: float = 0):
    user = await _get_user(request)
    result = None
    if cost > 0:
        result = purchasing_power_loss(cost, LIVE_MARKET["inflation"]["rate"])
    rp_result = None
    if profit > 0:
        rp_result = real_profit(profit, LIVE_MARKET["inflation"]["rate"])
    html = _jinja_env.get_template("purchasing_power.html").render(
        result=result, cost=cost, inflation=LIVE_MARKET["inflation"]["rate"],
        real_profit_result=rp_result, profit=profit, user=user,
    )
    return HTMLResponse(html)


@app.get("/indicators", response_class=HTMLResponse)
async def indicators_page(request: Request,
    calc: str = "", tnx_input: float = 0, inf_input: float = 0,
    pe_input: float = 0, tnx2_input: float = 0,
    idx_input: float = 0, inf2_input: float = 0, years_input: int = 1,
    earn_input: float = 0, tnx3_input: float = 0,
    vix_input: float = 0,
    amt_input: float = 0, inf3_input: float = 0, yrs_input: int = 5,
):
    inflation = LIVE_MARKET["inflation"]["rate"]
    calc_result = None
    inputs = {}

    if calc == "real_rate":
        tnx = tnx_input or MOCK_INDEXES["tnx"]["value"]
        inf = inf_input or inflation
        calc_result = {"type": "real_rate", "data": real_interest_rate(tnx, inf)}
        inputs = {"tnx": tnx, "inf": inf}
    elif calc == "erp":
        pe = pe_input or MOCK_INDEXES["sp500"]["pe_ratio"]
        tnx2 = tnx2_input or MOCK_INDEXES["tnx"]["value"]
        calc_result = {"type": "erp", "data": equity_risk_premium(pe, tnx2)}
        inputs = {"pe": pe, "tnx2": tnx2}
    elif calc == "infl_adj":
        idx = idx_input or MOCK_INDEXES["sp500"]["value"]
        inf2 = inf2_input or inflation
        yrs = years_input or 1
        calc_result = {"type": "infl_adj", "data": inflation_adjusted_index(idx, inf2, yrs)}
        inputs = {"idx": idx, "inf2": inf2, "years": yrs}
    elif calc == "fed_model":
        earn = earn_input or MOCK_INDEXES["sp500"]["earnings"]
        tnx3 = tnx3_input or MOCK_INDEXES["tnx"]["value"]
        calc_result = {"type": "fed_model", "data": sp500_fair_value_fed_model(earn, tnx3)}
        inputs = {"earn": earn, "tnx3": tnx3}
    elif calc == "vix_stress":
        vix = vix_input or MOCK_INDEXES["vix"]["value"]
        calc_result = {"type": "vix_stress", "data": vix_market_stress(vix)}
        inputs = {"vix": vix}
    elif calc == "pp_decay":
        amt = amt_input or 100000
        inf3 = inf3_input or inflation
        yrs = yrs_input or 5
        calc_result = {"type": "pp_decay", "data": purchasing_power_decay(amt, inf3, yrs)}
        inputs = {"amt": amt, "inf3": inf3, "yrs": yrs}

    user = await _get_user(request)
    html = _jinja_env.get_template("indicators.html").render(
        indexes=MOCK_INDEXES, inflation=inflation,
        calc_result=calc_result, inputs=inputs, user=user,
    )
    return HTMLResponse(html)


# --- MONTE CARLO SIMULATION ---

@app.get("/simulate", response_class=HTMLResponse)
async def simulate_page(request: Request, scenarios: int = 1000, confidence: float = 0.95):
    user = await _get_user(request)
    result = None
    if scenarios:
        result = monte_carlo_var(LIVE_MARKET, _profile(), scenarios=scenarios, confidence=confidence)
    html = _jinja_env.get_template("simulate.html").render(
        result=result, scenarios=scenarios, confidence=confidence,
        profile=_profile(), user=user,
    )
    return HTMLResponse(html)


# --- CASH FLOW FORECAST ---

@app.get("/cash-flow", response_class=HTMLResponse)
async def cash_flow_page(request: Request, months: int = 12):
    user = await _get_user(request)
    result = forecast_cash_flow(LIVE_MARKET, _profile(), months=months)
    html = _jinja_env.get_template("cash_flow.html").render(
        result=result, months=months, profile=_profile(), user=user,
    )
    return HTMLResponse(html)


# --- AUTH ---

def _get_token(request: Request) -> str:
    return request.cookies.get("session_token", "")

def _user_ctx(request: Request):
    token = _get_token(request)
    return None if not token else None  # resolved lazily in routes


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: str = ""):
    token = _get_token(request)
    user = await get_user_by_token(token) if token else None
    if user:
        return RedirectResponse(url="/track")
    html = _jinja_env.get_template("login.html").render(error=error, supabase_mode=_supabase_mode)
    return HTMLResponse(html)


@app.get("/login/submit", response_class=HTMLResponse)
async def login_submit(request: Request, email: str = "", password: str = ""):
    if not email or not password:
        return RedirectResponse(url="/login?error=Email+and+password+required")
    result = await login(email, password)
    if not result.get("ok"):
        return RedirectResponse(url=f"/login?error={result.get('error', 'Login+failed')}")
    resp = RedirectResponse(url="/track")
    resp.set_cookie(key="session_token", value=result["token"], max_age=86400 * 30, httponly=True)
    return resp


@app.get("/signup", response_class=HTMLResponse)
async def signup_page(request: Request, error: str = ""):
    token = _get_token(request)
    user = await get_user_by_token(token) if token else None
    if user:
        return RedirectResponse(url="/track")
    html = _jinja_env.get_template("signup.html").render(error=error, supabase_mode=_supabase_mode)
    return HTMLResponse(html)


@app.get("/signup/submit", response_class=HTMLResponse)
async def signup_submit(request: Request, name: str = "", email: str = "", password: str = ""):
    if not email or not password or not name:
        return RedirectResponse(url="/signup?error=All+fields+required")
    if len(password) < 6:
        return RedirectResponse(url="/signup?error=Password+must+be+at+least+6+characters")
    result = await signup(email, password, name)
    if not result.get("ok"):
        return RedirectResponse(url=f"/signup?error={result.get('error', 'Signup+failed')}")
    return RedirectResponse(url="/login")


@app.get("/logout", response_class=HTMLResponse)
async def logout_route(request: Request):
    token = _get_token(request)
    if token:
        await auth_logout(token)
    resp = RedirectResponse(url="/")
    resp.delete_cookie("session_token")
    return resp


# --- INCOME TRACKING (auth required) ---

@app.get("/track", response_class=HTMLResponse)
async def track_page(request: Request):
    token = _get_token(request)
    user = await get_user_by_token(token) if token else None
    if not user:
        return RedirectResponse(url="/login?error=Please+sign+in+to+track+income")
    records = await load_income_records(user["email"])
    html = _jinja_env.get_template("track.html").render(
        user=user, records=records, inflation=LIVE_MARKET["inflation"]["rate"],
        supabase_mode=_supabase_mode,
    )
    return HTMLResponse(html)


@app.get("/track/add", response_class=HTMLResponse)
async def track_add(request: Request, type: str = "income", category: str = "other", amount: float = 0, description: str = ""):
    token = _get_token(request)
    user = await get_user_by_token(token) if token else None
    if not user:
        return RedirectResponse(url="/login")
    record = {
        "type": type,
        "category": category,
        "amount": amount,
        "description": description,
        "date": str(__import__("datetime").datetime.utcnow().isoformat()),
    }
    await save_income_record(user["email"], record)
    return RedirectResponse(url="/track")


# --- PROFILE with auth persistence ---

@app.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request, saved: bool = False):
    token = _get_token(request)
    user = await get_user_by_token(token) if token else None
    if user:
        saved_profile = await auth_load_profile(user["email"])
        if saved_profile:
            ACTIVE_PROFILE.update(saved_profile)
    html = _jinja_env.get_template("profile.html").render(
        profile=ACTIVE_PROFILE, saved=saved, user=user, supabase_mode=_supabase_mode,
    )
    return HTMLResponse(html)


@app.get("/profile/save", response_class=HTMLResponse)
async def profile_save_route(request: Request,
    company_name: str = "My Company", industry: str = "software", tier: str = "mid",
    burn_rate: float = 600000, cash_reserves: float = 3000000, profit: float = 500000,
    fuel_pct: float = 5, payroll_pct: float = 50, materials_pct: float = 25, other_pct: float = 20,
    btc_holdings: float = 100000, gold_holdings: float = 50000, cash_holdings: float = 2000000,
    hedge_threshold: float = 5.0,
):
    ACTIVE_PROFILE["company"]["name"] = company_name
    ACTIVE_PROFILE["company"]["industry"] = industry
    ACTIVE_PROFILE["company"]["tier"] = tier
    ACTIVE_PROFILE["financials"]["monthly_burn_rate"] = burn_rate
    ACTIVE_PROFILE["financials"]["cash_reserves"] = cash_reserves
    ACTIVE_PROFILE["financials"]["nominal_profit_last_q"] = profit
    ACTIVE_PROFILE["financials"]["expense_breakdown"]["fuel_energy_pct"] = fuel_pct / 100
    ACTIVE_PROFILE["financials"]["expense_breakdown"]["payroll_pct"] = payroll_pct / 100
    ACTIVE_PROFILE["financials"]["expense_breakdown"]["materials_pct"] = materials_pct / 100
    ACTIVE_PROFILE["financials"]["expense_breakdown"]["other_pct"] = other_pct / 100
    ACTIVE_PROFILE["financials"]["asset_exposure"]["btc_holdings_usd"] = btc_holdings
    ACTIVE_PROFILE["financials"]["asset_exposure"]["gold_holdings_usd"] = gold_holdings
    ACTIVE_PROFILE["financials"]["asset_exposure"]["cash_usd"] = cash_holdings
    ACTIVE_PROFILE["risk_config"]["hedge_threshold_inflation"] = hedge_threshold

    token = _get_token(request)
    user = await get_user_by_token(token) if token else None
    if user:
        await auth_save_profile(user["email"], dict(ACTIVE_PROFILE))

    return await profile_page(request, saved=True)


# --- API ---

@app.get("/api/v1/market")
async def get_market():
    try:
        fresh = await fetch_market()
        LIVE_MARKET.update(fresh)
    except Exception:
        pass
    return LIVE_MARKET


@app.get("/api/v1/risk-score")
def risk_score_get(industry: str = "software"):
    profile = default_user_profile()
    profile["company"]["industry"] = industry
    return {"industry": industry, "sensitivities": get_sensitivity(industry), "risk": compute_risk_score(LIVE_MARKET, profile)}


@app.post("/api/v1/risk-score")
def risk_score_post(req: UserProfileRequest):
    return {"risk": compute_risk_score(LIVE_MARKET, req.user_profile), "sensitivities_used": get_sensitivity(req.user_profile.get("company", {}).get("industry", "unknown"))}


@app.post("/api/v1/real-profit")
def real_profit_endpoint(req: UserProfileRequest):
    nominal = req.user_profile.get("financials", {}).get("nominal_profit_last_q", 0)
    return real_profit(nominal, LIVE_MARKET["inflation"]["rate"])


@app.post("/api/v1/hedging-advisor")
def hedging_endpoint(req: UserProfileRequest):
    return hedging_advisor(LIVE_MARKET, req.user_profile)


@app.post("/api/v1/monte-carlo/var")
def monte_carlo_endpoint(req: UserProfileRequest):
    return monte_carlo_var(LIVE_MARKET, req.user_profile, scenarios=1000)


@app.post("/api/v1/cash-flow-forecast")
def cash_flow_endpoint(req: UserProfileRequest, months: int = 12):
    return forecast_cash_flow(LIVE_MARKET, req.user_profile, months=months)


@app.get("/api/v1/alerts/divergence")
def divergence_alerts():
    return {"alerts": compute_divergence_alerts()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
