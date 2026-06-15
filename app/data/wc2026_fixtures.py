"""The actual 2026 FIFA World Cup group stage — all 72 fixtures.

Real groups (final draw, 5 Dec 2025) and the real match calendar
(11–27 June 2026). Used as the authoritative fixture list when live providers
are unreachable, and as the offline source of truth for predictions.

Source rows are terse tuples: (date, kickoff_utc, group, home, away). Team names
match the published schedule; ratings.canonical() maps them to rating keys.
Kickoff times are representative — dates are exact.
"""
from __future__ import annotations

# (date "MM-DD", "HH:MM" UTC, group letter, home, away)
_SCHEDULE: list[tuple[str, str, str, str, str]] = [
    # Matchday 1
    ("06-11", "19:00", "A", "Mexico", "South Africa"),
    ("06-11", "22:00", "A", "South Korea", "Czechia"),
    ("06-12", "19:00", "B", "Canada", "Bosnia and Herzegovina"),
    ("06-12", "22:00", "D", "USA", "Paraguay"),
    ("06-13", "16:00", "B", "Qatar", "Switzerland"),
    ("06-13", "19:00", "C", "Brazil", "Morocco"),
    ("06-13", "22:00", "C", "Haiti", "Scotland"),
    ("06-13", "23:00", "D", "Australia", "Turkiye"),
    ("06-14", "16:00", "E", "Germany", "Curacao"),
    ("06-14", "18:00", "F", "Netherlands", "Japan"),
    ("06-14", "21:00", "E", "Ivory Coast", "Ecuador"),
    ("06-14", "23:00", "F", "Sweden", "Tunisia"),
    ("06-15", "16:00", "H", "Spain", "Cape Verde"),
    ("06-15", "18:00", "G", "Belgium", "Egypt"),
    ("06-15", "21:00", "H", "Saudi Arabia", "Uruguay"),
    ("06-15", "23:00", "G", "Iran", "New Zealand"),
    ("06-16", "16:00", "I", "France", "Senegal"),
    ("06-16", "18:00", "I", "Iraq", "Norway"),
    ("06-16", "21:00", "J", "Argentina", "Algeria"),
    ("06-16", "23:00", "J", "Austria", "Jordan"),
    ("06-17", "16:00", "K", "Portugal", "DR Congo"),
    ("06-17", "18:00", "L", "England", "Croatia"),
    ("06-17", "21:00", "L", "Ghana", "Panama"),
    ("06-17", "23:00", "K", "Uzbekistan", "Colombia"),
    # Matchday 2
    ("06-18", "16:00", "A", "Czechia", "South Africa"),
    ("06-18", "18:00", "B", "Switzerland", "Bosnia and Herzegovina"),
    ("06-18", "21:00", "B", "Canada", "Qatar"),
    ("06-18", "23:00", "A", "Mexico", "South Korea"),
    ("06-19", "16:00", "C", "Scotland", "Morocco"),
    ("06-19", "18:00", "D", "USA", "Australia"),
    ("06-19", "21:00", "C", "Brazil", "Haiti"),
    ("06-19", "23:00", "D", "Turkiye", "Paraguay"),
    ("06-20", "16:00", "F", "Netherlands", "Sweden"),
    ("06-20", "18:00", "E", "Germany", "Ivory Coast"),
    ("06-20", "21:00", "E", "Ecuador", "Curacao"),
    ("06-20", "23:00", "F", "Tunisia", "Japan"),
    ("06-21", "16:00", "H", "Spain", "Saudi Arabia"),
    ("06-21", "18:00", "G", "Belgium", "Iran"),
    ("06-21", "21:00", "H", "Uruguay", "Cape Verde"),
    ("06-21", "23:00", "G", "New Zealand", "Egypt"),
    ("06-22", "16:00", "J", "Argentina", "Austria"),
    ("06-22", "18:00", "I", "France", "Iraq"),
    ("06-22", "21:00", "I", "Norway", "Senegal"),
    ("06-22", "23:00", "J", "Jordan", "Algeria"),
    ("06-23", "16:00", "K", "Portugal", "Uzbekistan"),
    ("06-23", "18:00", "L", "England", "Ghana"),
    ("06-23", "21:00", "L", "Panama", "Croatia"),
    ("06-23", "23:00", "K", "Colombia", "DR Congo"),
    # Matchday 3 (simultaneous kickoffs)
    ("06-24", "19:00", "B", "Switzerland", "Canada"),
    ("06-24", "19:00", "B", "Bosnia and Herzegovina", "Qatar"),
    ("06-24", "23:00", "C", "Scotland", "Brazil"),
    ("06-24", "23:00", "C", "Morocco", "Haiti"),
    ("06-24", "01:00", "A", "Czechia", "Mexico"),
    ("06-24", "01:00", "A", "South Africa", "South Korea"),
    ("06-25", "19:00", "E", "Ecuador", "Germany"),
    ("06-25", "19:00", "E", "Curacao", "Ivory Coast"),
    ("06-25", "23:00", "F", "Japan", "Sweden"),
    ("06-25", "23:00", "F", "Tunisia", "Netherlands"),
    ("06-25", "01:00", "D", "Turkiye", "USA"),
    ("06-25", "01:00", "D", "Paraguay", "Australia"),
    ("06-26", "19:00", "I", "Norway", "France"),
    ("06-26", "19:00", "I", "Senegal", "Iraq"),
    ("06-26", "21:00", "H", "Cape Verde", "Saudi Arabia"),
    ("06-26", "21:00", "H", "Uruguay", "Spain"),
    ("06-26", "23:00", "G", "Egypt", "Iran"),
    ("06-26", "23:00", "G", "New Zealand", "Belgium"),
    ("06-27", "19:00", "L", "Panama", "England"),
    ("06-27", "19:00", "L", "Croatia", "Ghana"),
    ("06-27", "21:00", "K", "Colombia", "Portugal"),
    ("06-27", "21:00", "K", "DR Congo", "Uzbekistan"),
    ("06-27", "23:00", "J", "Algeria", "Austria"),
    ("06-27", "23:00", "J", "Jordan", "Argentina"),
]


def _build() -> list[dict]:
    out = []
    for i, (date, time, group, home, away) in enumerate(_SCHEDULE, start=1):
        out.append({
            "id": f"wc2026-{i:02d}",
            "home": home,
            "away": away,
            "utc_date": f"2026-{date}T{time}:00Z",
            "status": "upcoming",
            "round": f"Group {group}",
            "source": "schedule",
        })
    return out


WC2026_FIXTURES: list[dict] = _build()
