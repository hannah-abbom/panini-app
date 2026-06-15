"""FotMob public-JSON client.

FotMob exposes a JSON API used by its own web app. There is no official,
documented public API and the endpoints / required headers change from time to
time, so every call is defensive: on any error we return None and the caller
falls back to other sources or the bundled sample data. Be considerate with
request volume and respect FotMob's terms of service.
"""
from __future__ import annotations

from typing import Any

import httpx

BASE = "https://www.fotmob.com/api"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; PaniniPredictor/1.0; personal use)",
    "Accept": "application/json",
}
# FotMob's league id for the FIFA World Cup.
WORLD_CUP_LEAGUE_ID = 77


def _get(path: str, params: dict | None = None) -> Any | None:
    try:
        with httpx.Client(timeout=10.0, headers=HEADERS) as client:
            resp = client.get(f"{BASE}{path}", params=params)
            resp.raise_for_status()
            return resp.json()
    except (httpx.HTTPError, ValueError):
        return None


def world_cup_fixtures() -> list[dict] | None:
    """Upcoming World Cup fixtures, normalised to our common shape."""
    data = _get("/leagues", {"id": WORLD_CUP_LEAGUE_ID, "tab": "matches"})
    if not data:
        return None
    matches = (data.get("matches") or {}).get("allMatches") or []
    out: list[dict] = []
    for m in matches:
        try:
            out.append({
                "id": f"fotmob-{m['id']}",
                "home": m["home"]["name"],
                "away": m["away"]["name"],
                "utc_date": m.get("status", {}).get("utcTime"),
                "status": _status(m),
                "round": m.get("roundName") or m.get("round"),
                "source": "fotmob",
            })
        except (KeyError, TypeError):
            continue
    return out or None


def _status(match: dict) -> str:
    st = match.get("status", {})
    if st.get("finished"):
        return "finished"
    if st.get("started"):
        return "live"
    return "upcoming"
