"""Recent-form lookup and its effect on a team's effective rating.

The pure part (`form_delta`) is deterministic and unit-testable: a string of
recent results like "WWDLW" becomes a small Elo nudge, weighted so the most
recent match matters most and capped so a hot streak never dominates the base
rating. The network part (`team_form`) is defensive and returns None when
SofaScore is unreachable, so the model simply falls back to base ratings.
"""
from __future__ import annotations

from . import cache, sofascore

# Per-match weight (newest first). A recent win is worth ~+10 Elo, loss -10.
_WEIGHTS = [10.0, 7.0, 5.0, 3.0, 2.0, 1.0]
MAX_FORM_DELTA = 45.0


def form_delta(results: list[str]) -> float:
    """Turn a list like ['W','W','D','L'] (newest first) into an Elo nudge."""
    total = 0.0
    for i, r in enumerate(results[:len(_WEIGHTS)]):
        w = _WEIGHTS[i]
        if r == "W":
            total += w
        elif r == "L":
            total -= w
    return max(-MAX_FORM_DELTA, min(MAX_FORM_DELTA, total))


def team_form(name: str) -> dict | None:
    """Recent form for a team: {string, results, delta} or None if unavailable."""
    def fetch():
        tid = sofascore.search_team_id(name)
        if not tid:
            return None
        return sofascore.team_last_results(tid)

    matches = cache.get_or_fetch(f"form_{name}", fetch, ttl_minutes=720)
    if not matches:
        return None
    results = [m["result"] for m in matches]
    return {
        "string": "".join(results),
        "results": matches,
        "delta": round(form_delta(results), 1),
    }
