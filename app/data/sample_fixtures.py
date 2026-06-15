"""Bundled sample World Cup 2026 group-stage fixtures.

Used when live providers are unreachable (offline, blocked, or rate-limited) so
the app is always usable. Replace or extend freely - the fields here are the
common shape every data source is normalised to.
"""
from __future__ import annotations

SAMPLE_FIXTURES: list[dict] = [
    {"id": "sample-1", "home": "Argentina", "away": "Nigeria",
     "utc_date": "2026-06-16T19:00:00Z", "status": "upcoming",
     "round": "Group A", "source": "sample"},
    {"id": "sample-2", "home": "France", "away": "Mexico",
     "utc_date": "2026-06-16T22:00:00Z", "status": "upcoming",
     "round": "Group B", "source": "sample"},
    {"id": "sample-3", "home": "Spain", "away": "Japan",
     "utc_date": "2026-06-17T19:00:00Z", "status": "upcoming",
     "round": "Group C", "source": "sample"},
    {"id": "sample-4", "home": "England", "away": "Senegal",
     "utc_date": "2026-06-17T22:00:00Z", "status": "upcoming",
     "round": "Group D", "source": "sample"},
    {"id": "sample-5", "home": "Brazil", "away": "Croatia",
     "utc_date": "2026-06-18T19:00:00Z", "status": "upcoming",
     "round": "Group E", "source": "sample"},
    {"id": "sample-6", "home": "Portugal", "away": "United States",
     "utc_date": "2026-06-18T22:00:00Z", "status": "upcoming",
     "round": "Group F", "source": "sample"},
    {"id": "sample-7", "home": "Netherlands", "away": "Ecuador",
     "utc_date": "2026-06-19T19:00:00Z", "status": "upcoming",
     "round": "Group G", "source": "sample"},
    {"id": "sample-8", "home": "Germany", "away": "Morocco",
     "utc_date": "2026-06-19T22:00:00Z", "status": "upcoming",
     "round": "Group H", "source": "sample"},
    {"id": "sample-9", "home": "Belgium", "away": "Canada",
     "utc_date": "2026-06-20T19:00:00Z", "status": "upcoming",
     "round": "Group B", "source": "sample"},
    {"id": "sample-10", "home": "Uruguay", "away": "Korea Republic",
     "utc_date": "2026-06-20T22:00:00Z", "status": "upcoming",
     "round": "Group C", "source": "sample"},
    {"id": "sample-11", "home": "Italy", "away": "Switzerland",
     "utc_date": "2026-06-21T19:00:00Z", "status": "upcoming",
     "round": "Group D", "source": "sample"},
    {"id": "sample-12", "home": "Colombia", "away": "Australia",
     "utc_date": "2026-06-21T22:00:00Z", "status": "upcoming",
     "round": "Group E", "source": "sample"},
]
