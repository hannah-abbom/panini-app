"""Turn a prediction into an actionable betting tip.

From the full set of modelled markets we build a list of candidate selections,
each with the model's probability and its fair decimal odds, then pick the
strongest *sensible* one: high probability but not a trivial near-certainty
(we ignore odds below ~1.30). Confidence is graded from the probability, and a
1-3 star rating goes with it. A short accumulator of independent legs is also
offered per match.
"""
from __future__ import annotations

# The "bettable" sweet spot: meaningful odds, not a 1.05 near-certainty nor a
# long shot. Tips inside this band are preferred over trivial bankers.
SWEET_MIN = 1.40
SWEET_MAX = 2.80


def _odds(prob_pct: float) -> float:
    return round(100.0 / prob_pct, 2) if prob_pct > 0 else 99.0


def _confidence(prob: float) -> tuple[str, int]:
    if prob >= 72:
        return "High", 3
    if prob >= 62:
        return "Medium", 2
    return "Low", 1


def candidates(d: dict) -> list[dict]:
    """All sensible selections for a prediction dict, with prob + fair odds."""
    home, away = d["home"], d["away"]
    r, g, mk, st = d["result"], d["goals"], d["markets"], d["stats"]
    ou = g["over_under"]
    out = [
        (f"{home} to win", r["home_win"]),
        (f"{away} to win", r["away_win"]),
        ("Draw", r["draw"]),
        (f"{home} or draw (1X)", r["double_chance"]["1X"]),
        (f"{away} or draw (X2)", r["double_chance"]["X2"]),
        ("Both teams to score", g["btts"]["yes"]),
        ("No goal for one side", g["btts"]["no"]),
        ("Over 1.5 goals", ou["1.5"]["over"]),
        ("Over 2.5 goals", ou["2.5"]["over"]),
        ("Under 2.5 goals", ou["2.5"]["under"]),
        (f"{home} -1.5", mk["handicap"]["home_-1.5"]),
        (f"{away} +1.5", mk["handicap"]["away_+1.5"]),
        ("Over 8.5 corners", st["corners"]["lines"]["8.5"]["over"]),
        ("Over 9.5 corners", st["corners"]["lines"]["9.5"]["over"]),
        ("Over 3.5 cards", st["cards"]["lines"]["3.5"]["over"]),
        ("Over 4.5 cards", st["cards"]["lines"]["4.5"]["over"]),
    ]
    return [{"selection": s, "prob": p, "odds": _odds(p)} for s, p in out]


def _score(c: dict) -> float:
    """Prefer probable picks that sit in the bettable odds band."""
    if SWEET_MIN <= c["odds"] <= SWEET_MAX:
        return c["prob"]
    return c["prob"] * 0.55          # de-prioritise trivial bankers / long shots


def best_tip(d: dict) -> dict:
    """The single strongest *bettable* selection for a match."""
    best = max(candidates(d), key=_score)
    conf, stars = _confidence(best["prob"])
    return {**best, "confidence": conf, "stars": stars}


def match_accumulator(d: dict) -> dict:
    """A 2-leg same-match acca (result + a goals/stat leg) with combined odds."""
    cands = {c["selection"]: c for c in candidates(d)}
    legs = []
    # Strongest result-type leg.
    result_legs = [d["result"]["home_win"], d["result"]["away_win"]]
    if max(result_legs) >= 55:
        side = f"{d['home']} to win" if d["result"]["home_win"] >= d["result"]["away_win"] else f"{d['away']} to win"
        legs.append(cands[side])
    else:
        legs.append(cands[f"{d['home']} or draw (1X)"] if d["result"]["home_win"] >= d["result"]["away_win"]
                    else cands[f"{d['away']} or draw (X2)"])
    # Strongest goals/stat leg.
    extra = max([cands["Over 1.5 goals"], cands["Over 8.5 corners"], cands["Both teams to score"]],
                key=lambda c: c["prob"])
    legs.append(extra)
    combined = round(legs[0]["odds"] * legs[1]["odds"], 2)
    return {"legs": legs, "combined_odds": combined}
