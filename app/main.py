"""Panini - personal FIFA World Cup prediction site (FastAPI)."""
from __future__ import annotations

from fastapi import Depends, FastAPI, Form, HTTPException, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import store
from .auth import (COOKIE_NAME, SESSION_TTL_SECONDS, check_password,
                   issue_token, require_auth)
from .config import settings
from .data import form as form_data
from .data import sources
from .models import bracket, poisson, ratings

app = FastAPI(title="Panini", docs_url=None, redoc_url=None)


def _effective_elo(name: str, use_form: bool) -> tuple[float, dict | None]:
    """Base rating from the store, optionally nudged by recent form."""
    base = store.rating_for(name)
    info = None
    if use_form:
        info = form_data.team_form(name)
        if info:
            base += info["delta"]
    return base, info


# ---- Pages -----------------------------------------------------------------

@app.get("/")
def index():
    return FileResponse(settings.static_dir / "index.html")


@app.get("/login")
def login_page():
    return FileResponse(settings.static_dir / "login.html")


# ---- Auth ------------------------------------------------------------------

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

@app.get("/api/fixtures")
def api_fixtures(_: bool = Depends(require_auth)):
    data = sources.get_fixtures()
    enriched = []
    for fx in data["fixtures"]:
        pred = poisson.predict(fx["home"], fx["away"],
                               store.rating_for(fx["home"]),
                               store.rating_for(fx["away"]), neutral=True)
        enriched.append({**fx, "prediction": {
            "home_win": pred.result["home_win"],
            "draw": pred.result["draw"],
            "away_win": pred.result["away_win"],
            "most_likely_score": pred.expected["most_likely_score"],
            "total_goals": pred.expected["total"],
            "btts": pred.goals["btts"]["yes"],
            "over25": pred.goals["over_under"]["2.5"]["over"],
        }})
    return {"source": data["source"], "live": data["live"], "fixtures": enriched}


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
    return store.record_result(req.home, req.away, req.goals_home,
                               req.goals_away, neutral=req.neutral)


@app.get("/api/results")
def api_results(_: bool = Depends(require_auth)):
    return {"results": store.results_log()}


@app.post("/api/ratings/reset")
def api_reset(_: bool = Depends(require_auth)):
    store.reset()
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
