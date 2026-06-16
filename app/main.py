"""Panini - personal FIFA World Cup prediction site (FastAPI)."""
from __future__ import annotations

import time as _time

from fastapi import Cookie, Depends, FastAPI, Form, HTTPException, Response
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import accuracy, ai, db, store, users
from .auth import (COOKIE_NAME, SESSION_TTL_SECONDS, check_password,
                   issue_token, require_auth)
from .config import settings
from .data import form as form_data
from .data import news as news_data
from .data import sources
from .models import bracket, poisson, ratings, tips

app = FastAPI(title="Predictions", docs_url=None, redoc_url=None)
app.add_middleware(GZipMiddleware, minimum_size=600)

# Short-lived response cache for the heavy prediction endpoints. Bumping
# _cache_version invalidates everything (used when a result is recorded).
_resp_cache: dict = {}
_cache_version = 0


def _cached(key: str, ttl: float, build):
    now = _time.time()
    ent = _resp_cache.get(key)
    if ent and ent["v"] == _cache_version and now - ent["ts"] < ttl:
        return ent["data"]
    data = build()
    _resp_cache[key] = {"data": data, "ts": now, "v": _cache_version}
    return data


def _effective_elo(name: str, use_form: bool) -> tuple[float, dict | None]:
    """Base rating from the store, optionally nudged by recent form."""
    base = store.rating_for(name)
    info = None
    if use_form:
        info = form_data.team_form(name)
        if info:
            base += info["delta"]
    return base, info


def _wc_elo(name: str) -> float:
    """Rating for a World Cup fixture: base + host advantage if applicable."""
    base = store.rating_for(name)
    if ratings.is_host(name):
        base += ratings.HOST_BONUS
    return base


# ---- Pages -----------------------------------------------------------------

_NO_CACHE = {"Cache-Control": "no-store, max-age=0"}


@app.get("/")
def index():
    return FileResponse(settings.static_dir / "index.html", headers=_NO_CACHE)


@app.get("/login")
def login_page():
    # When the app is open, never show a password screen — bounce to the app.
    if not settings.require_auth:
        return RedirectResponse(url="/")
    return FileResponse(settings.static_dir / "login.html", headers=_NO_CACHE)


# ---- Auth ------------------------------------------------------------------

@app.get("/api/meta")
def api_meta():
    return {"auth_required": settings.require_auth, "ai_enabled": ai.ai_enabled()}


class ChatRequest(BaseModel):
    messages: list[dict]


@app.post("/api/chat")
def api_chat(req: ChatRequest, _: bool = Depends(require_auth)):
    last = next((m.get("content", "") for m in reversed(req.messages)
                 if m.get("role") == "user"), "")
    # Full Claude assistant when a key is configured; otherwise the built-in
    # model-driven responder so Predi AI always works.
    if ai.ai_enabled():
        try:
            return {"reply": ai.chat(req.messages), "enabled": True, "mode": "ai"}
        except Exception:
            pass
    return {"reply": ai.local_answer(last), "enabled": True, "mode": "local"}


@app.post("/api/login")
def api_login(password: str = Form(...)):
    if not check_password(password):
        raise HTTPException(status_code=401, detail="Wrong password")
    response = JSONResponse({"ok": True})
    response.set_cookie(COOKIE_NAME, issue_token(), max_age=SESSION_TTL_SECONDS,
                        httponly=True, samesite="lax")
    return response


@app.post("/api/logout")
def api_logout():
    response = JSONResponse({"ok": True})
    response.delete_cookie(COOKIE_NAME)
    return response


# ---- Fixtures + predictions ------------------------------------------------

def _build_fixtures():
    data = sources.get_fixtures()
    enriched = []
    for fx in data["fixtures"]:
        pred = poisson.predict(fx["home"], fx["away"],
                               _wc_elo(fx["home"]), _wc_elo(fx["away"]),
                               neutral=True)
        tip = tips.best_tip(pred.to_dict())
        enriched.append({**fx, "prediction": {
            "home_win": pred.result["home_win"],
            "draw": pred.result["draw"],
            "away_win": pred.result["away_win"],
            "most_likely_score": pred.expected["most_likely_score"],
            "total_goals": pred.expected["total"],
            "btts": pred.goals["btts"]["yes"],
            "over25": pred.goals["over_under"]["2.5"]["over"],
            "tip": tip,
        }})
    return {"source": data["source"], "live": data["live"], "fixtures": enriched}


@app.get("/api/fixtures")
def api_fixtures(_: bool = Depends(require_auth)):
    return _cached("fixtures", 20, _build_fixtures)


def _build_tips():
    data = sources.get_fixtures()
    board = []
    for fx in data["fixtures"]:
        if fx.get("status") == "finished":
            continue
        pred = poisson.predict(fx["home"], fx["away"],
                               _wc_elo(fx["home"]), _wc_elo(fx["away"]),
                               neutral=True).to_dict()
        tip = tips.best_tip(pred)
        board.append({
            "id": fx["id"], "home": fx["home"], "away": fx["away"],
            "round": fx["round"], "utc_date": fx["utc_date"], "tip": tip,
            "picks": tips.top_picks(pred, 3),
            "result": pred["result"],
            "acca": tips.match_accumulator(pred),
        })
    board.sort(key=lambda b: (-b["tip"]["stars"], -b["tip"]["prob"]))
    return {"tips": board, "bet_of_the_day": board[0] if board else None}


@app.get("/api/tips")
def api_tips(_: bool = Depends(require_auth)):
    """A betting-tips board: the best tip for every upcoming match."""
    return _cached("tips", 30, _build_tips)


class PredictRequest(BaseModel):
    home: str
    away: str
    neutral: bool = True
    use_form: bool = True


@app.post("/api/predict")
def api_predict(req: PredictRequest, _: bool = Depends(require_auth)):
    if not req.home or not req.away:
        raise HTTPException(status_code=400, detail="home and away are required")
    home_elo, home_form = _effective_elo(req.home, req.use_form)
    away_elo, away_form = _effective_elo(req.away, req.use_form)
    pred = poisson.predict(req.home, req.away, home_elo, away_elo,
                           neutral=req.neutral)
    out = pred.to_dict()
    out["form"] = {"home": home_form, "away": away_form}
    out["tip"] = tips.best_tip(out)
    out["accumulator"] = tips.match_accumulator(out)
    return out


class ValueRequest(BaseModel):
    probability: float
    odds: float


@app.post("/api/value")
def api_value(req: ValueRequest, _: bool = Depends(require_auth)):
    return poisson.value_bet(req.probability, req.odds)


# ---- Ratings / rankings ----------------------------------------------------

def _tier(elo: float) -> str:
    if elo >= 2000:
        return "Favourites"
    if elo >= 1850:
        return "Contenders"
    if elo >= 1750:
        return "Dark horses"
    return "Outsiders"


@app.get("/api/news")
def api_news(_: bool = Depends(require_auth)):
    return {"items": news_data.get_news()}


@app.get("/api/accuracy")
def api_accuracy(_: bool = Depends(require_auth)):
    return accuracy.compute()


# ---- User accounts (optional) ----------------------------------------------

USER_COOKIE = "user_session"


def current_user(user_session: str | None = Cookie(default=None)):
    return users.user_from_token(user_session)


def _require_user(u):
    if not u:
        raise HTTPException(status_code=401, detail="Please sign in.")
    return u


def _user_payload(u) -> dict:
    return {"user": {"email": u["email"], "plan": u["plan"]},
            "favourites": db.list_favs(u["id"]), "saved": db.list_saved(u["id"])}


class AuthRequest(BaseModel):
    email: str
    password: str


def _set_session(resp, uid: int):
    resp.set_cookie(USER_COOKIE, users.make_token(uid),
                    max_age=users.SESSION_TTL, httponly=True, samesite="lax")


@app.post("/api/auth/signup")
def api_signup(req: AuthRequest):
    email = req.email.strip().lower()
    if "@" not in email or "." not in email:
        raise HTTPException(400, "Enter a valid email address.")
    if len(req.password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters.")
    if db.get_user_by_email(email):
        raise HTTPException(409, "An account with that email already exists.")
    uid = db.create_user(email, users.hash_pw(req.password))
    resp = JSONResponse({"user": {"email": email, "plan": "free"}, "favourites": [], "saved": []})
    _set_session(resp, uid)
    return resp


@app.post("/api/auth/login")
def api_login_user(req: AuthRequest):
    u = db.get_user_by_email(req.email.strip().lower())
    if not u or not users.verify_pw(req.password, u["pw"]):
        raise HTTPException(401, "Wrong email or password.")
    resp = JSONResponse(_user_payload(u))
    _set_session(resp, u["id"])
    return resp


@app.post("/api/auth/logout")
def api_logout_user():
    resp = JSONResponse({"ok": True})
    resp.delete_cookie(USER_COOKIE)
    return resp


@app.get("/api/auth/me")
def api_me(u=Depends(current_user)):
    return _user_payload(u) if u else {"user": None}


class TeamRequest(BaseModel):
    team: str


@app.post("/api/favourites")
def api_add_fav(req: TeamRequest, u=Depends(current_user)):
    _require_user(u)
    db.add_fav(u["id"], req.team)
    return {"favourites": db.list_favs(u["id"])}


@app.post("/api/favourites/remove")
def api_remove_fav(req: TeamRequest, u=Depends(current_user)):
    _require_user(u)
    db.remove_fav(u["id"], req.team)
    return {"favourites": db.list_favs(u["id"])}


class SaveRequest(BaseModel):
    match: str
    selection: str
    odds: float


@app.post("/api/saved")
def api_save(req: SaveRequest, u=Depends(current_user)):
    _require_user(u)
    db.add_saved(u["id"], req.match, req.selection, req.odds)
    return {"saved": db.list_saved(u["id"])}


class SavedIdRequest(BaseModel):
    id: int


@app.post("/api/saved/remove")
def api_remove_saved(req: SavedIdRequest, u=Depends(current_user)):
    _require_user(u)
    db.remove_saved(u["id"], req.id)
    return {"saved": db.list_saved(u["id"])}


@app.get("/api/daily")
def api_daily(u=Depends(current_user)):
    """Daily AI picks — favourites' matches first, then the strongest tips."""
    board = _cached("tips", 30, _build_tips)["tips"]
    favs = set(db.list_favs(u["id"])) if u else set()
    if favs:
        board = sorted(board, key=lambda b: (0 if (b["home"] in favs or b["away"] in favs) else 1))
    return {"picks": board[:6], "favourites": list(favs)}


@app.get("/api/teams")
def api_teams(_: bool = Depends(require_auth)):
    teams = sorted(store.all_ratings().items(), key=lambda kv: -kv[1])
    return {"teams": [{"name": n, "elo": round(r)} for n, r in teams]}


@app.get("/api/rankings")
def api_rankings(_: bool = Depends(require_auth)):
    teams = sorted(store.all_ratings().items(), key=lambda kv: -kv[1])
    return {"teams": [
        {"rank": i + 1, "name": n, "elo": round(r), "tier": _tier(r)}
        for i, (n, r) in enumerate(teams)
    ]}


# ---- Results (drives Elo updates) ------------------------------------------

class ResultRequest(BaseModel):
    home: str
    away: str
    goals_home: int
    goals_away: int
    neutral: bool = True


@app.post("/api/result")
def api_result(req: ResultRequest, _: bool = Depends(require_auth)):
    global _cache_version
    out = store.record_result(req.home, req.away, req.goals_home,
                              req.goals_away, neutral=req.neutral)
    _cache_version += 1
    return out


@app.get("/api/results")
def api_results(_: bool = Depends(require_auth)):
    return {"results": store.results_log()}


@app.post("/api/ratings/reset")
def api_reset(_: bool = Depends(require_auth)):
    global _cache_version
    store.reset()
    _cache_version += 1
    return {"ok": True}


# ---- Knockout bracket ------------------------------------------------------

class BracketRequest(BaseModel):
    teams: list[str]
    sims: int = 20000


@app.post("/api/bracket")
def api_bracket(req: BracketRequest, _: bool = Depends(require_auth)):
    sims = max(1000, min(50000, req.sims))
    try:
        return bracket.simulate(req.teams, store.rating_for, sims=sims)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# ---- Static assets (mounted last so API routes win) ------------------------

app.mount("/static", StaticFiles(directory=settings.static_dir), name="static")
