"""Live result overlay — auto-updates finished scores as games complete.

Polls SofaScore for World Cup results across a window of recent days and
returns a map of finished scores keyed by canonical (home, away). Defensive and
cached: if the provider is unreachable it returns an empty map and the bundled
schedule/results are used unchanged. On a real server (e.g. the deployment) this
keeps the fixtures list current without a code change.
"""
from __future__ import annotations

from datetime import date, timedelta

from ..models import ratings
from . import cache, sofascore


def _fetch_live_results() -> dict:
    merged: dict = {}
    today = date.today()
    for offset in range(-3, 2):
        day = (today + timedelta(days=offset)).isoformat()
        res = sofascore.world_cup_results(day)
        if res:
            for (home, away), score in res.items():
                merged[f"{ratings.canonical(home)}|{ratings.canonical(away)}"] = score
    return merged


def live_results() -> dict:
    """Cached map "home|away" (canonical) -> [goals_home, goals_away]."""
    try:
        return cache.get_or_fetch("live_results", _fetch_live_results, ttl_minutes=5) or {}
    except Exception:
        return {}


def overlay(fixtures: list[dict]) -> list[dict]:
    """Apply any live finished scores onto fixtures (status + score)."""
    live = live_results()
    if not live:
        return fixtures
    out = []
    for fx in fixtures:
        key = f"{ratings.canonical(fx['home'])}|{ratings.canonical(fx['away'])}"
        if key in live and fx.get("status") != "finished":
            gh, ga = live[key]
            fx = {**fx, "status": "finished", "goals_home": gh,
                  "goals_away": ga, "score": f"{gh}-{ga}"}
        out.append(fx)
    return out
