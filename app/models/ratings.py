"""Seed Elo ratings for national teams.

These are World-Football-Elo style strength ratings (eloratings.net scale),
hand-seeded for the 2026 World Cup contenders as of mid-2026. They are a
starting point: the engine updates them as real results come in, and you can
edit any value here. Unknown teams fall back to DEFAULT_RATING.
"""
from __future__ import annotations

DEFAULT_RATING = 1700.0

SEED_RATINGS: dict[str, float] = {
    "Argentina": 2105,
    "France": 2080,
    "Spain": 2070,
    "England": 2010,
    "Brazil": 2005,
    "Portugal": 1995,
    "Netherlands": 1990,
    "Belgium": 1945,
    "Germany": 1930,
    "Italy": 1925,
    "Croatia": 1900,
    "Uruguay": 1900,
    "Colombia": 1880,
    "Morocco": 1865,
    "Switzerland": 1840,
    "United States": 1825,
    "Mexico": 1820,
    "Japan": 1815,
    "Senegal": 1810,
    "Denmark": 1805,
    "Ecuador": 1790,
    "Austria": 1785,
    "Korea Republic": 1775,
    "Sweden": 1770,
    "Serbia": 1765,
    "Ukraine": 1760,
    "Peru": 1745,
    "Poland": 1745,
    "Nigeria": 1740,
    "Australia": 1735,
    "Egypt": 1730,
    "Turkey": 1730,
    "Canada": 1725,
    "Norway": 1720,
    "Wales": 1715,
    "Chile": 1715,
    "Ivory Coast": 1710,
    "Cameroon": 1705,
    "Ghana": 1700,
    "Tunisia": 1695,
    "Algeria": 1695,
    "Paraguay": 1690,
    "Czechia": 1690,
    "Scotland": 1685,
    "Greece": 1680,
    "Hungary": 1675,
    "Romania": 1660,
    "Costa Rica": 1655,
    "Saudi Arabia": 1640,
    "Iran": 1700,
    "Qatar": 1640,
    "Panama": 1635,
    "Jamaica": 1620,
    "New Zealand": 1560,
}

# Common name variants from data providers -> our canonical key.
ALIASES: dict[str, str] = {
    "USA": "United States",
    "US": "United States",
    "South Korea": "Korea Republic",
    "Korea": "Korea Republic",
    "Cote d'Ivoire": "Ivory Coast",
    "Czech Republic": "Czechia",
    "Turkiye": "Turkey",
    "Turkía": "Turkey",
}


def canonical(name: str) -> str:
    name = (name or "").strip()
    return ALIASES.get(name, name)


def rating_for(name: str) -> float:
    return SEED_RATINGS.get(canonical(name), DEFAULT_RATING)
