"""World-Football-Elo update logic.

Standard Elo with a World-Cup weight and a goal-difference multiplier, so a
4-0 win moves ratings more than a 1-0. Used to keep ratings current as real
results arrive. See https://www.eloratings.net/about for the methodology this
mirrors.
"""
from __future__ import annotations

# K-factor weight for World Cup finals matches (eloratings uses 60 for WC).
K_WORLD_CUP = 60.0
# Home advantage in Elo points. World Cup matches are effectively neutral,
# except for the host nations; pass neutral=False to apply it.
HOME_ADVANTAGE = 65.0


def expected_score(elo_a: float, elo_b: float, home: bool = False,
                   neutral: bool = True) -> float:
    """Probability (0..1) that team A wins, treating a draw as half."""
    adv = 0.0 if neutral else (HOME_ADVANTAGE if home else -HOME_ADVANTAGE)
    diff = (elo_a + adv) - elo_b
    return 1.0 / (1.0 + 10.0 ** (-diff / 400.0))


def _goal_multiplier(goal_diff: int) -> float:
    g = abs(goal_diff)
    if g <= 1:
        return 1.0
    if g == 2:
        return 1.5
    return (11.0 + g) / 8.0


def update(elo_a: float, elo_b: float, goals_a: int, goals_b: int,
           k: float = K_WORLD_CUP, neutral: bool = True) -> tuple[float, float]:
    """Return the new (elo_a, elo_b) after a result goals_a-goals_b."""
    exp_a = expected_score(elo_a, elo_b, home=True, neutral=neutral)
    if goals_a > goals_b:
        result = 1.0
    elif goals_a < goals_b:
        result = 0.0
    else:
        result = 0.5
    mult = _goal_multiplier(goals_a - goals_b)
    delta = k * mult * (result - exp_a)
    return elo_a + delta, elo_b - delta
