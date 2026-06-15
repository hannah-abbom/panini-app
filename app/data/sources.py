"""Aggregate fixtures from all data sources, with a graceful fallback chain.

Order of preference: FotMob -> SofaScore -> bundled sample data. Whatever we
get is cached (see cache.py) so a single slow/blocked provider does not make
the site unusable. Everything is normalised to the same fixture shape:

    {id, home, away, utc_date, status, round, source}
"""
from __future__ import annotations

from datetime import date, timedelta

from . import cache, fotmob, live, sofascore
from .wc2026_fixtures import WC2026_FIXTURES


def _fetch_live() -> list[dict]:
    fixtures = fotmob.world_cup_fixtures()
    if fixtures:
        return fixtures

    # SofaScore is queried per-day; sweep a two-week window around today.
    collected: list[dict] = []
    today = date.today()
    for offset in range(-1, 14):
        day = (today + timedelta(days=offset)).isoformat()
        events = sofascore.scheduled_football(day)
        if events:
            collected.extend(events)
    return collected


def get_fixtures() -> dict:
    """Return fixtures plus a note about which source was actually used."""
    try:
        fixtures = cache.get_or_fetch("world_cup_fixtures", _fetch_live)
    except Exception:
        fixtures = []

    if fixtures:
        return {"fixtures": fixtures, "source": fixtures[0].get("source"),
                "live": True}
    # Overlay any live finished scores onto the bundled schedule so results
    # update automatically when the provider is reachable.
    return {"fixtures": live.overlay(WC2026_FIXTURES),
            "source": "2026 World Cup schedule", "live": False}
