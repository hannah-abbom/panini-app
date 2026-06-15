"""Match prediction engine: Elo -> expected goals -> Dixon-Coles/Poisson.

Pipeline:
  1. Turn the two teams' Elo ratings into an expected goal *supremacy*
     (how many goals the favourite is expected to win by) and an expected
     *total* number of goals in the match.
  2. Split those into per-team scoring rates (lambda_home, lambda_away).
  3. Build the full score matrix with independent Poissons, then apply the
     Dixon-Coles low-score correction (rho) which fixes the well-known
     under-counting of 0-0 / 1-0 / 1-1 results.
  4. Read every market off that matrix: 1X2, double chance, over/under,
     both-teams-to-score, correct score.

A separate helper turns any probability + bookmaker odds into an edge and a
Kelly-criterion stake, which is what makes this useful for finding value.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from . import elo

MAX_GOALS = 10                 # score matrix goes 0..MAX_GOALS for each team
ELO_PER_GOAL = 165.0           # Elo gap that corresponds to ~1 goal of supremacy
BASE_TOTAL_GOALS = 2.65        # average goals in a balanced World Cup match
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


@dataclass
class Prediction:
    home: str
    away: str
    home_elo: float
    away_elo: float
    lambda_home: float
    lambda_away: float
    result: dict        # 1X2 + double chance probabilities
    goals: dict         # over/under + BTTS
    expected: dict      # expected goals + most likely / fair lines
    correct_scores: list  # top scorelines

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
            "expected": self.expected,
            "correct_scores": self.correct_scores,
        }


def predict(home: str, away: str, home_elo: float, away_elo: float,
            neutral: bool = True) -> Prediction:
    lam_h, lam_a = _expected_lambdas(home_elo, away_elo, neutral=neutral)
    m = score_matrix(lam_h, lam_a)

    p_home = np.tril(m, -1).sum()   # home goals > away goals
    p_away = np.triu(m, 1).sum()    # away goals > home goals
    p_draw = np.trace(m)

    # Over / under and BTTS read straight off the matrix.
    idx = np.add.outer(np.arange(MAX_GOALS + 1), np.arange(MAX_GOALS + 1))
    overs = {}
    for line in (1.5, 2.5, 3.5):
        over = m[idx > line].sum()
        overs[str(line)] = {"over": _pct(over), "under": _pct(1 - over)}
    btts_yes = m[1:, 1:].sum()

    # Most likely scorelines.
    flat = [((i, j), m[i, j]) for i in range(MAX_GOALS + 1)
            for j in range(MAX_GOALS + 1)]
    flat.sort(key=lambda x: x[1], reverse=True)
    correct_scores = [
        {"score": f"{i}-{j}", "prob": _pct(p)} for (i, j), p in flat[:6]
    ]

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
    }
    goals = {
        "over_under": overs,
        "btts": {"yes": _pct(btts_yes), "no": _pct(1 - btts_yes)},
    }
    expected = {
        "goals_home": round(lam_h, 2),
        "goals_away": round(lam_a, 2),
        "total": round(lam_h + lam_a, 2),
        "supremacy": round(lam_h - lam_a, 2),
        "most_likely_score": correct_scores[0]["score"],
    }
    return Prediction(home, away, home_elo, away_elo, lam_h, lam_a,
                      result, goals, expected, correct_scores)


def _fair_odds(p: float) -> float | None:
    return round(1.0 / p, 2) if p > 1e-9 else None


def value_bet(prob_pct: float, decimal_odds: float) -> dict:
    """Edge and Kelly stake for a probability (%) against bookmaker odds."""
    p = max(0.0, min(1.0, prob_pct / 100.0))
    if decimal_odds <= 1.0:
        return {"edge_pct": 0.0, "kelly_pct": 0.0, "value": False}
    edge = p * decimal_odds - 1.0                       # expected return per unit
    kelly = (p * decimal_odds - 1.0) / (decimal_odds - 1.0)
    kelly = max(0.0, kelly)
    return {
        "edge_pct": round(edge * 100.0, 1),
        "kelly_pct": round(kelly * 100.0, 1),
        "half_kelly_pct": round(kelly * 50.0, 1),
        "value": edge > 0.0,
    }
