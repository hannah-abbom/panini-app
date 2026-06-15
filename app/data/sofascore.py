"""SofaScore public-JSON client.

Like the FotMob client this talks to the undocumented JSON API behind
SofaScore's own site. Endpoints can change or rate-limit, so calls are
defensive and return None on failure. Respect SofaScore's terms of service and
keep request volume low (we cache aggressively in cache.py).
"""
from __future__ import annotations

from typing import Any

import httpx

BASE = "https://api.sofascore.com/api/v1"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; PaniniPredictor/1.0; personal use)",
    "Accept": "application/json",
}


def _get(path: str) -> Any | None:
    try:
        with httpx.Client(timeout=10.0, headers=HEADERS) as client:
            resp = client.get(f"{BASE}{path}")
            resp.raise_for_status()
            return resp.json()
    except (httpx.HTTPError, ValueError):
        return None


def scheduled_football(date_iso: str) -> list[dict] | None:
    """All scheduled football events for a date (YYYY-MM-DD), World Cup only."""
    data = _get(f"/sport/football/scheduled-events/{date_iso}")
    if not data:
        return None
    out: list[dict] = []
    for ev in data.get("events", []):
        tournament = (ev.get("tournament") or {}).get("name", "")
        if "World Cup" not in tournament:
            continue
        try:
            out.append({
                "id": f"sofascore-{ev['id']}",
                "home": ev["homeTeam"]["name"],
                "away": ev["awayTeam"]["name"],
                "utc_date": ev.get("startTimestamp"),
                "status": ev.get("status", {}).get("type", "upcoming"),
                "round": tournament,
                "source": "sofascore",
            })
        except (KeyError, TypeError):
            continue
    return out or None
