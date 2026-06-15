"""Match-stat model: corners, cards, shots on target and fouls.

These drive the popular "stat" betting markets. We don't have live per-match
feeds in every environment, so the model derives expectations from the same
inputs as the goal model (each team's expected goals + Elo) anchored to real
World Cup baselines:

  * ~9.6 corners per game        (FootyStats / corner-stats, recent World Cups)
  * ~24 fouls per game
  * ~4.0 yellow cards per game
  * ~32% of shots on target are scored; ~35% of shots are on target

The logic: shots on target scale with expected goals; corners with attacking
dominance; fouls and cards fall more on the side defending against the stronger
attack, with extra cards in tight, tense games. Markets are read off Poisson
distributions on those expected totals.
"""
from __future__ import annotations

import math

TOTAL_CORNERS_BASE = 9.6
TOTAL_FOULS_BASE = 23.5
TOTAL_CARDS_BASE = 4.0
SOT_CONVERSION = 0.32      # goals per shot on target
SOT_SHARE_OF_SHOTS = 0.35  # share of shots that are on target


def _pois_over(mean: float, line: float) -> float:
    """P(X > line) for a Poisson(mean), line is a half-integer."""
    k = math.floor(line)
    cdf = sum(math.exp(-mean) * mean ** i / math.factorial(i) for i in range(k + 1))
    return round((1.0 - cdf) * 100.0, 1)


def _lines(mean: float, lines: list[float]) -> dict:
    return {str(l): {"over": _pois_over(mean, l), "under": round(100 - _pois_over(mean, l), 1)}
            for l in lines}


def match_stats(lam_home: float, lam_away: float,
                home_elo: float, away_elo: float) -> dict:
    # Shots on target track expected goals; total shots from the SoT ratio.
    sot_h = lam_home / SOT_CONVERSION
    sot_a = lam_away / SOT_CONVERSION
    shots_h = sot_h / SOT_SHARE_OF_SHOTS
    shots_a = sot_a / SOT_SHARE_OF_SHOTS
    share_h = shots_h / max(0.1, shots_h + shots_a)   # home attacking share

    def compress(s: float, factor: float) -> float:
        # Pull a share toward 0.5 — real stat splits are far less extreme
        # than the goal-expectation split, even in big mismatches.
        return 0.5 + (s - 0.5) * factor

    # Corners: scale with attacking dominance, split (tempered) by it.
    total_corners = TOTAL_CORNERS_BASE * (1.0 + 0.12 * abs(share_h - 0.5) * 2)
    corner_share = compress(share_h, 0.65)
    corners_h = max(1.0, total_corners * corner_share)
    corners_a = max(1.0, total_corners * (1 - corner_share))

    # Fouls: you foul more defending against the stronger attack (tempered),
    # with a realistic floor for both sides.
    foul_share_h = compress(1 - share_h, 0.5)
    fouls_h = max(5.0, TOTAL_FOULS_BASE * foul_share_h)
    fouls_a = max(5.0, TOTAL_FOULS_BASE * (1 - foul_share_h))
    total_fouls = fouls_h + fouls_a

    # Cards: track fouls, plus extra in tight games (closeness raises tension).
    tension = 1.0 + 0.30 * (1 - abs(share_h - 0.5) * 2)
    total_cards = TOTAL_CARDS_BASE * tension
    cards_h = total_cards * (fouls_h / total_fouls)
    cards_a = total_cards * (fouls_a / total_fouls)

    total_sot = sot_h + sot_a

    def block(h, a, lines):
        t = h + a
        return {"home": round(h, 1), "away": round(a, 1), "total": round(t, 1),
                "lines": _lines(t, lines)}

    return {
        "corners": block(corners_h, corners_a, [8.5, 9.5, 10.5]),
        "cards": block(cards_h, cards_a, [3.5, 4.5, 5.5]),
        "shots_on_target": block(sot_h, sot_a, [6.5, 7.5, 8.5]),
        "fouls": {"home": round(fouls_h, 1), "away": round(fouls_a, 1),
                  "total": round(total_fouls, 1)},
    }
