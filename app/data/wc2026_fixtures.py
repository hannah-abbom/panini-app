"""The actual 2026 FIFA World Cup group stage — all 72 fixtures.

Real groups (final draw, 5 Dec 2025), the real match calendar with exact UTC
kickoff times (11–27 June 2026), and the real results of matches already played.
Used as the authoritative fixture list when live providers are unreachable, and
as the offline source of truth for predictions.

PLAYED_RESULTS feeds the rating engine (see store.py) so ratings reflect what has
actually happened so far.
"""
from __future__ import annotations

# (utc kickoff ISO, group letter, home, away)
_SCHEDULE: list[tuple[str, str, str, str]] = [
    # Matchday 1
    ("2026-06-11T19:00:00Z", "A", "Mexico", "South Africa"),
    ("2026-06-12T02:00:00Z", "A", "South Korea", "Czechia"),
    ("2026-06-12T19:00:00Z", "B", "Canada", "Bosnia and Herzegovina"),
    ("2026-06-13T01:00:00Z", "D", "USA", "Paraguay"),
    ("2026-06-13T19:00:00Z", "B", "Qatar", "Switzerland"),
    ("2026-06-13T22:00:00Z", "C", "Brazil", "Morocco"),
    ("2026-06-14T01:00:00Z", "C", "Haiti", "Scotland"),
    ("2026-06-14T04:00:00Z", "D", "Australia", "Turkiye"),
    ("2026-06-14T17:00:00Z", "E", "Germany", "Curacao"),
    ("2026-06-14T20:00:00Z", "F", "Netherlands", "Japan"),
    ("2026-06-14T23:00:00Z", "E", "Ivory Coast", "Ecuador"),
    ("2026-06-15T02:00:00Z", "F", "Sweden", "Tunisia"),
    ("2026-06-15T16:00:00Z", "H", "Spain", "Cape Verde"),
    ("2026-06-15T19:00:00Z", "G", "Belgium", "Egypt"),
    ("2026-06-15T22:00:00Z", "H", "Saudi Arabia", "Uruguay"),
    ("2026-06-16T01:00:00Z", "G", "Iran", "New Zealand"),
    ("2026-06-16T19:00:00Z", "I", "France", "Senegal"),
    ("2026-06-16T22:00:00Z", "I", "Iraq", "Norway"),
    ("2026-06-17T01:00:00Z", "J", "Argentina", "Algeria"),
    ("2026-06-17T04:00:00Z", "J", "Austria", "Jordan"),
    ("2026-06-17T17:00:00Z", "K", "Portugal", "DR Congo"),
    ("2026-06-17T20:00:00Z", "L", "England", "Croatia"),
    ("2026-06-17T23:00:00Z", "L", "Ghana", "Panama"),
    ("2026-06-18T02:00:00Z", "K", "Uzbekistan", "Colombia"),
    # Matchday 2
    ("2026-06-18T16:00:00Z", "A", "Czechia", "South Africa"),
    ("2026-06-18T19:00:00Z", "B", "Switzerland", "Bosnia and Herzegovina"),
    ("2026-06-18T22:00:00Z", "B", "Canada", "Qatar"),
    ("2026-06-19T01:00:00Z", "A", "Mexico", "South Korea"),
    ("2026-06-19T19:00:00Z", "D", "USA", "Australia"),
    ("2026-06-19T22:00:00Z", "C", "Scotland", "Morocco"),
    ("2026-06-20T00:30:00Z", "C", "Brazil", "Haiti"),
    ("2026-06-20T03:00:00Z", "D", "Turkiye", "Paraguay"),
    ("2026-06-20T17:00:00Z", "F", "Netherlands", "Sweden"),
    ("2026-06-20T20:00:00Z", "E", "Germany", "Ivory Coast"),
    ("2026-06-21T03:00:00Z", "E", "Ecuador", "Curacao"),
    ("2026-06-21T04:00:00Z", "F", "Tunisia", "Japan"),
    ("2026-06-21T16:00:00Z", "H", "Spain", "Saudi Arabia"),
    ("2026-06-21T19:00:00Z", "G", "Belgium", "Iran"),
    ("2026-06-21T22:00:00Z", "H", "Uruguay", "Cape Verde"),
    ("2026-06-22T01:00:00Z", "G", "New Zealand", "Egypt"),
    ("2026-06-22T17:00:00Z", "J", "Argentina", "Austria"),
    ("2026-06-22T21:00:00Z", "I", "France", "Iraq"),
    ("2026-06-23T00:00:00Z", "I", "Norway", "Senegal"),
    ("2026-06-23T03:00:00Z", "J", "Jordan", "Algeria"),
    ("2026-06-23T17:00:00Z", "K", "Portugal", "Uzbekistan"),
    ("2026-06-23T20:00:00Z", "L", "England", "Ghana"),
    ("2026-06-23T23:00:00Z", "L", "Panama", "Croatia"),
    ("2026-06-24T02:00:00Z", "K", "Colombia", "DR Congo"),
    # Matchday 3 (simultaneous kickoffs)
    ("2026-06-24T19:00:00Z", "B", "Switzerland", "Canada"),
    ("2026-06-24T19:00:00Z", "B", "Bosnia and Herzegovina", "Qatar"),
    ("2026-06-24T22:00:00Z", "C", "Scotland", "Brazil"),
    ("2026-06-24T22:00:00Z", "C", "Morocco", "Haiti"),
    ("2026-06-25T01:00:00Z", "A", "Czechia", "Mexico"),
    ("2026-06-25T01:00:00Z", "A", "South Africa", "South Korea"),
    ("2026-06-25T20:00:00Z", "E", "Ecuador", "Germany"),
    ("2026-06-25T20:00:00Z", "E", "Curacao", "Ivory Coast"),
    ("2026-06-25T23:00:00Z", "F", "Japan", "Sweden"),
    ("2026-06-25T23:00:00Z", "F", "Tunisia", "Netherlands"),
    ("2026-06-26T02:00:00Z", "D", "Turkiye", "USA"),
    ("2026-06-26T02:00:00Z", "D", "Paraguay", "Australia"),
    ("2026-06-26T19:00:00Z", "I", "Norway", "France"),
    ("2026-06-26T19:00:00Z", "I", "Senegal", "Iraq"),
    ("2026-06-27T00:00:00Z", "H", "Cape Verde", "Saudi Arabia"),
    ("2026-06-27T00:00:00Z", "H", "Uruguay", "Spain"),
    ("2026-06-27T03:00:00Z", "G", "Egypt", "Iran"),
    ("2026-06-27T03:00:00Z", "G", "New Zealand", "Belgium"),
    ("2026-06-27T21:00:00Z", "L", "Panama", "England"),
    ("2026-06-27T21:00:00Z", "L", "Croatia", "Ghana"),
    ("2026-06-27T23:30:00Z", "K", "Colombia", "Portugal"),
    ("2026-06-27T23:30:00Z", "K", "DR Congo", "Uzbekistan"),
    ("2026-06-28T02:00:00Z", "J", "Algeria", "Austria"),
    ("2026-06-28T02:00:00Z", "J", "Jordan", "Argentina"),
]

# Real results of matches already played (home, away, goals_home, goals_away).
PLAYED_RESULTS: list[tuple[str, str, int, int]] = [
    ("Mexico", "South Africa", 2, 0),
    ("South Korea", "Czechia", 2, 1),
    ("Canada", "Bosnia and Herzegovina", 1, 1),
    ("USA", "Paraguay", 4, 1),
    ("Qatar", "Switzerland", 1, 1),
    ("Brazil", "Morocco", 1, 1),
    ("Haiti", "Scotland", 0, 1),
    ("Australia", "Turkiye", 2, 0),
    ("Germany", "Curacao", 7, 1),
    ("Netherlands", "Japan", 2, 2),
    ("Ivory Coast", "Ecuador", 1, 0),
    ("Sweden", "Tunisia", 5, 1),
]

_RESULT_MAP = {(h, a): (gh, ga) for h, a, gh, ga in PLAYED_RESULTS}


def _build() -> list[dict]:
    out = []
    for i, (utc, group, home, away) in enumerate(_SCHEDULE, start=1):
        fx = {
            "id": f"wc2026-{i:02d}",
            "home": home,
            "away": away,
            "utc_date": utc,
            "status": "upcoming",
            "round": f"Group {group}",
            "source": "schedule",
        }
        if (home, away) in _RESULT_MAP:
            gh, ga = _RESULT_MAP[(home, away)]
            fx.update(status="finished", goals_home=gh, goals_away=ga,
                      score=f"{gh}-{ga}")
        out.append(fx)
    return out


WC2026_FIXTURES: list[dict] = _build()
