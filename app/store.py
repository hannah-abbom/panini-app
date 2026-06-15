"""Persistent rating store.

Seed ratings in ratings.py are the starting point. When you record a real
result, we update both teams' Elo and persist the override + a result-log entry
to a JSON file in .data/ so it survives restarts. Effective rating = seed rating
overlaid with any stored override.
"""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path

from .config import BASE_DIR
from .data import statsbomb
from .data.wc2026_fixtures import PLAYED_RESULTS
from .models import elo, ratings

DATA_DIR = BASE_DIR / ".data"
STORE_PATH = DATA_DIR / "store.json"
_lock = threading.Lock()


def _base_ratings() -> dict[str, float]:
    """Seed ratings with the already-played World Cup results folded in.

    Deterministic and independent of the mutable store, so a fresh deploy
    always reflects what has actually happened so far.
    """
    r = dict(ratings.SEED_RATINGS)
    # Real-results prior from StatsBomb open data (bounded, defensive).
    for team, delta in statsbomb.team_deltas().items():
        if team in r:
            r[team] = round(r[team] + delta, 1)
    for home, away, gh, ga in PLAYED_RESULTS:
        h, a = ratings.canonical(home), ratings.canonical(away)
        rh = r.get(h, ratings.DEFAULT_RATING)
        ra = r.get(a, ratings.DEFAULT_RATING)
        nh, na = elo.update(rh, ra, gh, ga, neutral=True)
        r[h], r[a] = round(nh, 1), round(na, 1)
    return r


def _load() -> dict:
    if STORE_PATH.exists():
        try:
            return json.loads(STORE_PATH.read_text())
        except json.JSONDecodeError:
            pass
    return {"overrides": {}, "results": [], "updated": None}


def _save(state: dict) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    state["updated"] = time.time()
    STORE_PATH.write_text(json.dumps(state, indent=2))


def rating_for(name: str) -> float:
    """Effective rating: base (seed + played results) plus any override."""
    key = ratings.canonical(name)
    state = _load()
    if key in state["overrides"]:
        return float(state["overrides"][key])
    return _base_ratings().get(key, ratings.DEFAULT_RATING)


def all_ratings() -> dict[str, float]:
    """Every known team's current effective rating."""
    state = _load()
    merged = _base_ratings()
    merged.update({k: float(v) for k, v in state["overrides"].items()})
    return merged


def results_log() -> list[dict]:
    return _load()["results"]


def record_result(home: str, away: str, goals_home: int, goals_away: int,
                  neutral: bool = True) -> dict:
    """Apply a finished result, update both teams' Elo, and persist it."""
    h_key = ratings.canonical(home)
    a_key = ratings.canonical(away)
    with _lock:
        state = _load()
        base = _base_ratings()
        h_before = state["overrides"].get(h_key, base.get(h_key, ratings.DEFAULT_RATING))
        a_before = state["overrides"].get(a_key, base.get(a_key, ratings.DEFAULT_RATING))
        h_after, a_after = elo.update(float(h_before), float(a_before),
                                      goals_home, goals_away, neutral=neutral)
        state["overrides"][h_key] = round(h_after, 1)
        state["overrides"][a_key] = round(a_after, 1)
        state["results"].insert(0, {
            "home": h_key, "away": a_key,
            "goals_home": goals_home, "goals_away": goals_away,
            "neutral": neutral, "ts": time.time(),
            "home_delta": round(h_after - h_before, 1),
            "away_delta": round(a_after - a_before, 1),
        })
        state["results"] = state["results"][:200]
        _save(state)
    return {
        "home": h_key, "away": a_key,
        "home_before": round(float(h_before)), "home_after": round(h_after),
        "away_before": round(float(a_before)), "away_after": round(a_after),
        "home_delta": round(h_after - float(h_before), 1),
        "away_delta": round(a_after - float(a_before), 1),
    }


def reset() -> None:
    """Wipe all overrides and the result log, back to seed ratings."""
    with _lock:
        _save({"overrides": {}, "results": []})
