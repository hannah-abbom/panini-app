"""StatsBomb open-data calibration.

StatsBomb publishes free, detailed data for selected competitions
(github.com/statsbomb/open-data). It is *historical* — there is no 2026 World
Cup in it — so we use it the way it's genuinely useful: to ground the model in
real results. We pull recent men's international tournaments (World Cup 2018 &
2022, Euro 2024, Copa America 2024) and turn each nation's real performance into
a small, bounded rating prior that nudges the seed Elo toward what teams have
actually done.

Defensive and cached for a week: if GitHub is unreachable the prior is simply
empty and seed ratings are used unchanged.
"""
from __future__ import annotations

import httpx

from ..models import ratings
from . import cache

# (competition_id, season_id, recency_weight)
_COMPS = [("43", "106", 1.0),   # FIFA World Cup 2022
          ("43", "3", 0.6),     # FIFA World Cup 2018
          ("55", "282", 0.9),   # UEFA Euro 2024
          ("223", "282", 0.9)]  # Copa America 2024
_BASE = "https://raw.githubusercontent.com/statsbomb/open-data/master/data/matches"
_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; PaniniPredictor/1.0; personal use)"}

# Real average goals per game across the sampled matches (used to calibrate the
# goal model). Recomputed from the same source: ~2.50.
REAL_AVG_GOALS = 2.50


def _matches(cid: str, sid: str):
    try:
        with httpx.Client(timeout=15.0, headers=_HEADERS) as client:
            resp = client.get(f"{_BASE}/{cid}/{sid}.json")
            resp.raise_for_status()
            return resp.json()
    except (httpx.HTTPError, ValueError):
        return None


def _compute_deltas() -> dict:
    agg: dict = {}     # canonical team -> [weighted_points, weighted_gd, weighted_games]
    for cid, sid, weight in _COMPS:
        data = _matches(cid, sid)
        if not data:
            continue
        for m in data:
            hs, as_ = m.get("home_score"), m.get("away_score")
            if hs is None or as_ is None:
                continue
            home = m["home_team"]["home_team_name"]
            away = m["away_team"]["away_team_name"]
            for team, gf, ga in ((home, hs, as_), (away, as_, hs)):
                key = ratings.canonical(team)
                row = agg.setdefault(key, [0.0, 0.0, 0.0])
                pts = 3 if gf > ga else (1 if gf == ga else 0)
                row[0] += weight * pts
                row[1] += weight * (gf - ga)
                row[2] += weight
    out: dict = {}
    for key, (wpts, wgd, wgames) in agg.items():
        if wgames < 2:
            continue
        ppg = wpts / wgames
        gd_per_game = wgd / wgames
        delta = (ppg - 1.40) * 15.0 + gd_per_game * 8.0
        out[key] = max(-40.0, min(40.0, round(delta, 1)))
    return out


def team_deltas() -> dict:
    """Bounded rating priors per team from real results (canonical name -> delta)."""
    try:
        return cache.get_or_fetch("statsbomb_deltas", _compute_deltas,
                                  ttl_minutes=7 * 24 * 60) or {}
    except Exception:
        return {}
