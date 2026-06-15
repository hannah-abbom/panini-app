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


def search_team_id(name: str) -> int | None:
    """Resolve a national team name to a SofaScore team id."""
    data = _get(f"/search/all?q={httpx.QueryParams({'q': name})['q']}")
    if not data:
        return None
    for res in data.get("results", []):
        entity = res.get("entity", {})
        if res.get("type") == "team" and name.lower() in entity.get("name", "").lower():
            return entity.get("id")
    return None


def team_last_results(team_id: int, limit: int = 6) -> list[dict] | None:
    """Most recent finished matches for a team, newest first."""
    data = _get(f"/team/{team_id}/events/last/0")
    if not data:
        return None
    out: list[dict] = []
    for ev in reversed(data.get("events", [])):
        if ev.get("status", {}).get("type") != "finished":
            continue
        try:
            home = ev["homeTeam"]["name"]
            away = ev["awayTeam"]["name"]
            gh = ev["homeScore"]["current"]
            ga = ev["awayScore"]["current"]
            is_home = ev["homeTeam"]["id"] == team_id
            gf, goals_against = (gh, ga) if is_home else (ga, gh)
            outcome = "W" if gf > goals_against else ("L" if gf < goals_against else "D")
            out.append({
                "opponent": away if is_home else home,
                "gf": gf, "ga": goals_against, "result": outcome,
            })
        except (KeyError, TypeError):
            continue
        if len(out) >= limit:
            break
    return out or None


def world_cup_results(date_iso: str) -> dict | None:
    """Finished World Cup scores for a date, keyed by (home, away) -> (gh, ga)."""
    data = _get(f"/sport/football/scheduled-events/{date_iso}")
    if not data:
        return None
    out: dict = {}
    for ev in data.get("events", []):
        if "World Cup" not in (ev.get("tournament") or {}).get("name", ""):
            continue
        if ev.get("status", {}).get("type") != "finished":
            continue
        try:
            out[(ev["homeTeam"]["name"], ev["awayTeam"]["name"])] = (
                ev["homeScore"]["current"], ev["awayScore"]["current"])
        except (KeyError, TypeError):
            continue
    return out or None


def world_cup_live(date_iso: str) -> dict | None:
    """In-progress World Cup matches: (home, away) -> (gh, ga)."""
    data = _get(f"/sport/football/scheduled-events/{date_iso}")
    if not data:
        return None
    out: dict = {}
    for ev in data.get("events", []):
        if "World Cup" not in (ev.get("tournament") or {}).get("name", ""):
            continue
        if ev.get("status", {}).get("type") != "inprogress":
            continue
        try:
            out[(ev["homeTeam"]["name"], ev["awayTeam"]["name"])] = (
                ev["homeScore"].get("current", 0), ev["awayScore"].get("current", 0))
        except (KeyError, TypeError):
            continue
    return out or None


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
