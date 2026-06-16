"""Single-elimination bracket simulator.

Given an ordered list of teams (a power of two: 2, 4, 8, 16, 32), we precompute
the pairwise win probability for every possible knockout tie, then run a Monte
Carlo over the bracket. The result is each team's probability of reaching each
round and lifting the trophy.
"""
from __future__ import annotations

import random

from . import poisson


def _rounds_for(n: int) -> list[str]:
    names = {2: ["Final"], 4: ["Semi-final", "Final"],
             8: ["Quarter-final", "Semi-final", "Final"],
             16: ["Round of 16", "Quarter-final", "Semi-final", "Final"],
             32: ["Round of 32", "Round of 16", "Quarter-final",
                  "Semi-final", "Final"]}
    return names.get(n, [f"Round {i+1}" for i in range(n.bit_length() - 1)])


def simulate(teams: list[str], rating_of, sims: int = 20000) -> dict:
    """teams: ordered seeds. rating_of: name -> Elo. Returns per-team odds."""
    n = len(teams)
    if n < 2 or (n & (n - 1)) != 0:
        raise ValueError("number of teams must be a power of two (2,4,8,16,32)")

    elos = {t: rating_of(t) for t in teams}
    # Precompute P(a beats b) for every ordered pair once.
    win = {}
    for a in teams:
        for b in teams:
            if a != b and (a, b) not in win:
                p = poisson.advance_probability(elos[a], elos[b], neutral=True)
                win[(a, b)] = p
                win[(b, a)] = 1.0 - p

    rounds = _rounds_for(n)
    champ = {t: 0 for t in teams}
    reach = {t: {r: 0 for r in rounds} for t in teams}

    for _ in range(sims):
        alive = list(teams)
        for r in rounds:
            nxt = []
            for i in range(0, len(alive), 2):
                a, b = alive[i], alive[i + 1]
                winner = a if random.random() < win[(a, b)] else b
                reach[winner][r] += 1
                nxt.append(winner)
            alive = nxt
        champ[alive[0]] += 1

    out = []
    for t in teams:
        row = {"team": t, "elo": round(elos[t]),
               "champion": round(100.0 * champ[t] / sims, 1)}
        for r in rounds:
            row[r] = round(100.0 * reach[t][r] / sims, 1)
        out.append(row)
    out.sort(key=lambda x: -x["champion"])
    return {"rounds": rounds, "teams": out, "sims": sims}
