"""Elo ratings for the 48 teams at the 2026 FIFA World Cup.

World-Football-Elo style strength ratings (eloratings.net scale), seeded for the
2026 finals as of mid-2026. They are a starting point: the engine updates them
as real results come in, and you can edit any value here. Unknown teams fall
back to DEFAULT_RATING.

The three host nations (USA, Mexico, Canada) play their group games at home, so
the prediction layer adds HOST_BONUS to their effective rating for those games.
"""
from __future__ import annotations

DEFAULT_RATING = 1650.0

# Host nations get a home-advantage bump in their own group games.
HOST_TEAMS = {"United States", "Mexico", "Canada"}
HOST_BONUS = 45.0

SEED_RATINGS: dict[str, float] = {
    "Argentina": 2100,
    "Spain": 2080,
    "France": 2070,
    "Brazil": 2015,
    "England": 2005,
    "Portugal": 1990,
    "Netherlands": 1980,
    "Belgium": 1940,
    "Germany": 1935,
    "Croatia": 1900,
    "Uruguay": 1895,
    "Colombia": 1875,
    "Morocco": 1860,
    "Switzerland": 1830,
    "United States": 1825,
    "Norway": 1820,
    "Japan": 1810,
    "Mexico": 1805,
    "Senegal": 1805,
    "Ecuador": 1785,
    "Austria": 1780,
    "Korea Republic": 1770,
    "Sweden": 1765,
    "Egypt": 1730,
    "Australia": 1730,
    "Turkey": 1725,
    "Canada": 1720,
    "Ivory Coast": 1715,
    "Ghana": 1700,
    "Iran": 1700,
    "Czechia": 1690,
    "Algeria": 1690,
    "Tunisia": 1690,
    "Scotland": 1685,
    "Paraguay": 1685,
    "DR Congo": 1660,
    "Bosnia and Herzegovina": 1650,
    "South Africa": 1640,
    "Qatar": 1640,
    "Saudi Arabia": 1635,
    "Panama": 1630,
    "Uzbekistan": 1620,
    "Iraq": 1600,
    "Jordan": 1580,
    "Cape Verde": 1575,
    "New Zealand": 1560,
    "Curacao": 1505,
    "Haiti": 1500,
}

# Common name variants from data providers / fixtures -> our canonical key.
ALIASES: dict[str, str] = {
    "USA": "United States",
    "US": "United States",
    "United States of America": "United States",
    "South Korea": "Korea Republic",
    "Korea": "Korea Republic",
    "Korea, Republic of": "Korea Republic",
    "Turkiye": "Turkey",
    "Türkiye": "Turkey",
    "Czech Republic": "Czechia",
    "Cote d'Ivoire": "Ivory Coast",
    "Côte d'Ivoire": "Ivory Coast",
    "Congo DR": "DR Congo",
    "DRC": "DR Congo",
    "Democratic Republic of the Congo": "DR Congo",
    "Curaçao": "Curacao",
    "Bosnia & Herzegovina": "Bosnia and Herzegovina",
    "Bosnia": "Bosnia and Herzegovina",
    "Cabo Verde": "Cape Verde",
}


def canonical(name: str) -> str:
    name = (name or "").strip()
    return ALIASES.get(name, name)


def rating_for(name: str) -> float:
    return SEED_RATINGS.get(canonical(name), DEFAULT_RATING)


def is_host(name: str) -> bool:
    return canonical(name) in HOST_TEAMS
