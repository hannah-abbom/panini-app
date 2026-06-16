"""Live result overlay — auto-updates finished and in-progress games.

Polls SofaScore for World Cup matches across a window of recent days and returns
finished scores and in-progress (live) scores keyed by canonical "home|away".
Defensive and cached (90s): if the provider is unreachable nothing changes and
the bundled schedule/results are used. On a real server this keeps both final
results and live in-play scores current without a code change.
"""
from __future__ import annotations

from datetime import date, timedelta

from ..models import ratings
from . import cache, sofascore


def _key(home: str, away: str) -> str:
    return f"{ratings.canonical(home)}|{ratings.canonical(away)}"


def _fetch_state() -> dict:
    finished: dict = {}
    inplay: dict = {}
    today = date.today()
    for offset in range(-3, 2):
        day = (today + timedelta(days=offset)).isoformat()
        res = sofascore.world_cup_results(day)
        if res:
            for (h, a), score in res.items():
                finished[_key(h, a)] = list(score)
        liv = sofascore.world_cup_live(day)
        if liv:
            for (h, a), score in liv.items():
                inplay[_key(h, a)] = list(score)
    return {"finished": finished, "live": inplay}


def state() -> dict:
    try:
        return cache.get_or_fetch("live_state", _fetch_state, ttl_minutes=1.5) \
            or {"finished": {}, "live": {}}
    except Exception:
        return {"finished": {}, "live": {}}


def overlay(fixtures: list[dict]) -> list[dict]:
    """Apply live in-play and finished scores onto fixtures."""
    s = state()
    if not s["finished"] and not s["live"]:
        return fixtures
    out = []
    for fx in fixtures:
        k = _key(fx["home"], fx["away"])
        if k in s["live"]:
            gh, ga = s["live"][k]
            fx = {**fx, "status": "live", "goals_home": gh, "goals_away": ga,
                  "score": f"{gh}-{ga}"}
        elif k in s["finished"] and fx.get("status") != "finished":
            gh, ga = s["finished"][k]
            fx = {**fx, "status": "finished", "goals_home": gh, "goals_away": ga,
                  "score": f"{gh}-{ga}"}
        out.append(fx)
    return out
