"""Panini - personal FIFA World Cup prediction site (FastAPI)."""
from __future__ import annotations

from fastapi import Depends, FastAPI, Form, HTTPException, Response
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .auth import (COOKIE_NAME, SESSION_TTL_SECONDS, check_password,
                   issue_token, require_auth)
from .config import settings
from .data import sources
from .models import poisson, ratings

app = FastAPI(title="Panini", docs_url=None, redoc_url=None)


# ---- Pages -----------------------------------------------------------------

@app.get("/")
def index():
    return FileResponse(settings.static_dir / "index.html")


@app.get("/login")
def login_page():
    return FileResponse(settings.static_dir / "login.html")


# ---- Auth ------------------------------------------------------------------

@app.post("/api/login")
def api_login(response: Response, password: str = Form(...)):
    if not check_password(password):
        raise HTTPException(status_code=401, detail="Wrong password")
    response = JSONResponse({"ok": True})
    response.set_cookie(
        COOKIE_NAME, issue_token(), max_age=SESSION_TTL_SECONDS,
        httponly=True, samesite="lax",
    )
    return response


@app.post("/api/logout")
def api_logout():
    response = JSONResponse({"ok": True})
    response.delete_cookie(COOKIE_NAME)
    return response


# ---- Predictions -----------------------------------------------------------

@app.get("/api/fixtures")
def api_fixtures(_: bool = Depends(require_auth)):
    """Upcoming fixtures, each with a baked-in prediction summary."""
    data = sources.get_fixtures()
    enriched = []
    for fx in data["fixtures"]:
        pred = poisson.predict(
            fx["home"], fx["away"],
            ratings.rating_for(fx["home"]), ratings.rating_for(fx["away"]),
            neutral=True,
        )
        enriched.append({**fx, "prediction": {
            "home_win": pred.result["home_win"],
            "draw": pred.result["draw"],
            "away_win": pred.result["away_win"],
            "most_likely_score": pred.expected["most_likely_score"],
            "total_goals": pred.expected["total"],
        }})
    return {"source": data["source"], "live": data["live"],
            "fixtures": enriched}


class PredictRequest(BaseModel):
    home: str
    away: str
    neutral: bool = True


@app.post("/api/predict")
def api_predict(req: PredictRequest, _: bool = Depends(require_auth)):
    if not req.home or not req.away:
        raise HTTPException(status_code=400, detail="home and away are required")
    pred = poisson.predict(
        req.home, req.away,
        ratings.rating_for(req.home), ratings.rating_for(req.away),
        neutral=req.neutral,
    )
    return pred.to_dict()


class ValueRequest(BaseModel):
    probability: float          # percent, e.g. 42.5
    odds: float                 # decimal odds, e.g. 2.40


@app.post("/api/value")
def api_value(req: ValueRequest, _: bool = Depends(require_auth)):
    return poisson.value_bet(req.probability, req.odds)


@app.get("/api/teams")
def api_teams(_: bool = Depends(require_auth)):
    """All known teams and their current Elo, for the manual matchup picker."""
    teams = sorted(ratings.SEED_RATINGS.items(), key=lambda kv: -kv[1])
    return {"teams": [{"name": n, "elo": round(r)} for n, r in teams]}


# ---- Static assets (mounted last so API routes win) ------------------------

app.mount("/static", StaticFiles(directory=settings.static_dir), name="static")
