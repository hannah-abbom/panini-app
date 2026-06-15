"""Match prediction engine: Elo -> expected goals -> Dixon-Coles/Poisson.

Pipeline:
  1. Turn the two teams' Elo ratings into an expected goal *supremacy* (how
     many goals the favourite is expected to win by) and an expected *total*
     number of goals in the match.
  2. Split those into per-team scoring rates (lambda_home, lambda_away).
  3. Build the full score matrix with independent Poissons, then apply the
     Dixon-Coles low-score correction (rho) which fixes the well-known
     under-counting of 0-0 / 1-0 / 1-1 results.
  4. Read every market off that matrix: 1X2, double chance, over/under, BTTS,
     clean sheets, win-to-nil, handicaps, goal distribution, correct score.

A separate helper turns any probability + bookmaker odds into an edge and a
Kelly-criterion stake, which is what makes this useful for finding value.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from . import elo
from . import stats as stats_model

MAX_GOALS = 10                 # score matrix goes 0..MAX_GOALS for each team
ELO_PER_GOAL = 165.0           # Elo gap that corresponds to ~1 goal of supremacy
BASE_TOTAL_GOALS = 2.55        # avg goals/game, calibrated on StatsBomb open data (~2.50)
TOTAL_GOALS_SPREAD = 0.18      # mismatches produce slightly more total goals
DIXON_COLES_RHO = -0.06        # low-score dependency correction
MIN_LAMBDA = 0.18              # floor so no team is ever exactly zero


def _expected_lambdas(home_elo: float, away_elo: float,
                      neutral: bool = True) -> tuple[float, float]:
    adv = 0.0 if neutral else elo.HOME_ADVANTAGE
    diff = (home_elo + adv) - away_elo
    supremacy = diff / ELO_PER_GOAL
    total = BASE_TOTAL_GOALS + TOTAL_GOALS_SPREAD * abs(supremacy)
    lam_home = max(MIN_LAMBDA, (total + supremacy) / 2.0)
    lam_away = max(MIN_LAMBDA, (total - supremacy) / 2.0)
    return lam_home, lam_away


def _dc_tau(i: int, j: int, lam: float, mu: float, rho: float) -> float:
    """Dixon-Coles correction factor for the low-score cells."""
    if i == 0 and j == 0:
        return 1.0 - lam * mu * rho
    if i == 0 and j == 1:
        return 1.0 + lam * rho
    if i == 1 and j == 0:
        return 1.0 + mu * rho
    if i == 1 and j == 1:
        return 1.0 - rho
    return 1.0


def score_matrix(lam_home: float, lam_away: float) -> np.ndarray:
    """Probability of every scoreline home_goals x away_goals."""
    home = np.array([math.exp(-lam_home) * lam_home ** i / math.factorial(i)
                     for i in range(MAX_GOALS + 1)])
    away = np.array([math.exp(-lam_away) * lam_away ** j / math.factorial(j)
                     for j in range(MAX_GOALS + 1)])
    matrix = np.outer(home, away)
    for i in range(2):
        for j in range(2):
            matrix[i, j] *= _dc_tau(i, j, lam_home, lam_away, DIXON_COLES_RHO)
    return matrix / matrix.sum()


def _pct(x: float) -> float:
    return round(float(x) * 100.0, 1)


def _fair_odds(p: float) -> float | None:
    return round(1.0 / p, 2) if p > 1e-9 else None


@dataclass
class Prediction:
    home: str
    away: str
    home_elo: float
    away_elo: float
    lambda_home: float
    lambda_away: float
    result: dict
    goals: dict
    markets: dict
    expected: dict
    correct_scores: list
    matrix: list        # 6x6 grid (goals 0..5) in percent, for the heatmap
    advance: dict       # knockout: probability each side goes through
    stats: dict         # corners, cards, shots on target, fouls + their markets

    def to_dict(self) -> dict:
        return {
            "home": self.home,
            "away": self.away,
            "home_elo": round(self.home_elo),
            "away_elo": round(self.away_elo),
            "lambda_home": round(self.lambda_home, 2),
            "lambda_away": round(self.lambda_away, 2),
            "result": self.result,
            "goals": self.goals,
            "markets": self.markets,
            "expected": self.expected,
            "correct_scores": self.correct_scores,
            "matrix": self.matrix,
            "advance": self.advance,
            "stats": self.stats,
        }


def predict(home: str, away: str, home_elo: float, away_elo: float,
            neutral: bool = True) -> Prediction:
    lam_h, lam_a = _expected_lambdas(home_elo, away_elo, neutral=neutral)
    m = score_matrix(lam_h, lam_a)

    p_home = float(np.tril(m, -1).sum())   # home goals > away goals
    p_away = float(np.triu(m, 1).sum())    # away goals > home goals
    p_draw = float(np.trace(m))

    # Over / under and BTTS read straight off the matrix.
    idx = np.add.outer(np.arange(MAX_GOALS + 1), np.arange(MAX_GOALS + 1))
    overs = {}
    for line in (0.5, 1.5, 2.5, 3.5, 4.5):
        over = float(m[idx > line].sum())
        overs[str(line)] = {"over": _pct(over), "under": _pct(1 - over)}
    btts_yes = float(m[1:, 1:].sum())

    # Goal-count distribution (total goals in the match).
    total_dist = []
    for n in range(0, 7):
        if n < 6:
            p = float(m[idx == n].sum())
        else:
            p = float(m[idx >= 6].sum())
        total_dist.append({"goals": (f"{n}+" if n == 6 else str(n)),
                           "prob": _pct(p)})

    # Clean sheets and win-to-nil.
    cs_home = float(m[:, 0].sum())          # away fails to score
    cs_away = float(m[0, :].sum())          # home fails to score
    wtn_home = float(np.tril(m, -1)[:, 0].sum())
    wtn_away = float(np.triu(m, 1)[0, :].sum())

    # Handicaps (no push; goal lines).
    margin = np.subtract.outer(np.arange(MAX_GOALS + 1),
                               np.arange(MAX_GOALS + 1))
    handicaps = {
        "home_-1.5": _pct(float(m[margin >= 2].sum())),
        "home_+1.5": _pct(float(m[margin >= -1].sum())),
        "away_-1.5": _pct(float(m[margin <= -2].sum())),
        "away_+1.5": _pct(float(m[margin <= 1].sum())),
    }

    # Most likely scorelines.
    flat = [((i, j), m[i, j]) for i in range(MAX_GOALS + 1)
            for j in range(MAX_GOALS + 1)]
    flat.sort(key=lambda x: x[1], reverse=True)
    correct_scores = [
        {"score": f"{i}-{j}", "prob": _pct(p)} for (i, j), p in flat[:6]
    ]

    # 6x6 heatmap grid (goals 0..5).
    matrix6 = [[_pct(m[i, j]) for j in range(6)] for i in range(6)]

    # Knockout: who goes through if a draw is resolved by ET / penalties.
    es = elo.expected_score(home_elo, away_elo, home=True, neutral=neutral)
    adv_home = p_home + p_draw * es
    advance = {"home": _pct(adv_home), "away": _pct(1 - adv_home)}

    result = {
        "home_win": _pct(p_home),
        "draw": _pct(p_draw),
        "away_win": _pct(p_away),
        "double_chance": {
            "1X": _pct(p_home + p_draw),
            "12": _pct(p_home + p_away),
            "X2": _pct(p_draw + p_away),
        },
        "fair_odds": {
            "home": _fair_odds(p_home),
            "draw": _fair_odds(p_draw),
            "away": _fair_odds(p_away),
        },
        "expected_points": {
            "home": round(3 * p_home + p_draw, 2),
            "away": round(3 * p_away + p_draw, 2),
        },
    }
    goals = {
        "over_under": overs,
        "btts": {"yes": _pct(btts_yes), "no": _pct(1 - btts_yes)},
        "distribution": total_dist,
    }
    markets = {
        "clean_sheet": {"home": _pct(cs_home), "away": _pct(cs_away)},
        "win_to_nil": {"home": _pct(wtn_home), "away": _pct(wtn_away)},
        "handicap": handicaps,
    }
    expected = {
        "goals_home": round(lam_h, 2),
        "goals_away": round(lam_a, 2),
        "total": round(lam_h + lam_a, 2),
        "supremacy": round(lam_h - lam_a, 2),
        "most_likely_score": correct_scores[0]["score"],
    }
    match_stats = stats_model.match_stats(lam_h, lam_a, home_elo, away_elo)
    return Prediction(home, away, home_elo, away_elo, lam_h, lam_a,
                      result, goals, markets, expected, correct_scores,
                      matrix6, advance, match_stats)


def advance_probability(home_elo: float, away_elo: float,
                        neutral: bool = True) -> float:
    """Probability the home/first team wins a knockout tie (0..1)."""
    lam_h, lam_a = _expected_lambdas(home_elo, away_elo, neutral=neutral)
    m = score_matrix(lam_h, lam_a)
    p_home = float(np.tril(m, -1).sum())
    p_draw = float(np.trace(m))
    es = elo.expected_score(home_elo, away_elo, home=True, neutral=neutral)
    return p_home + p_draw * es


def value_bet(prob_pct: float, decimal_odds: float) -> dict:
    """Edge and Kelly stake for a probability (%) against bookmaker odds."""
    p = max(0.0, min(1.0, prob_pct / 100.0))
    if decimal_odds <= 1.0:
        return {"edge_pct": 0.0, "kelly_pct": 0.0, "half_kelly_pct": 0.0,
                "value": False, "implied_pct": 0.0}
    edge = p * decimal_odds - 1.0                       # expected return per unit
    kelly = max(0.0, (p * decimal_odds - 1.0) / (decimal_odds - 1.0))
    return {
        "edge_pct": round(edge * 100.0, 1),
        "kelly_pct": round(kelly * 100.0, 1),
        "half_kelly_pct": round(kelly * 50.0, 1),
        "implied_pct": round(100.0 / decimal_odds, 1),
        "value": edge > 0.0,
    }
