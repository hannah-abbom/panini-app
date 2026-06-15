"""AI accuracy tracker — backtest the model against real results.

For every finished match we reconstruct the model's PRE-match prediction using
only the ratings as they stood before that game (a walk-forward backtest — no
peeking at the result), compare it to what actually happened, and tally accuracy
across markets. Updates automatically as new results land.
"""
from __future__ import annotations

from .data import cache, statsbomb
from .data.wc2026_fixtures import PLAYED_RESULTS, WC2026_FIXTURES
from .models import elo, poisson, ratings


def _base() -> dict:
    r = dict(ratings.SEED_RATINGS)
    for t, d in statsbomb.team_deltas().items():
        if t in r:
            r[t] = round(r[t] + d, 1)
    return r


def _elo(r: dict, name: str) -> float:
    base = r.get(ratings.canonical(name), ratings.DEFAULT_RATING)
    return base + ratings.HOST_BONUS if ratings.is_host(name) else base


def _pct(x: float) -> float:
    return round(x * 100.0, 1)


def compute() -> dict:
    def build() -> dict:
        r = _base()
        res = {(h, a): (gh, ga) for h, a, gh, ga in PLAYED_RESULTS}
        log, n = [], 0
        r1 = sc = ou = bt = 0
        conf_sum = 0.0
        for fx in WC2026_FIXTURES:                 # chronological
            key = (fx["home"], fx["away"])
            if key not in res:
                continue
            gh, ga = res[key]
            pred = poisson.predict(fx["home"], fx["away"],
                                   _elo(r, fx["home"]), _elo(r, fx["away"])).to_dict()
            probs = {"home": pred["result"]["home_win"],
                     "draw": pred["result"]["draw"],
                     "away": pred["result"]["away_win"]}
            pred_oc = max(probs, key=probs.get)
            actual_oc = "home" if gh > ga else ("away" if ga > gh else "draw")
            n += 1
            hit = pred_oc == actual_oc
            r1 += hit
            score_hit = pred["expected"]["most_likely_score"] == f"{gh}-{ga}"
            sc += score_hit
            over = (gh + ga) > 2.5
            ou += (over == (pred["goals"]["over_under"]["2.5"]["over"] >= 50))
            btts = gh > 0 and ga > 0
            bt += (btts == (pred["goals"]["btts"]["yes"] >= 50))
            conf_sum += probs[actual_oc] / 100.0
            label = {"home": fx["home"], "draw": "Draw", "away": fx["away"]}
            log.append({
                "home": fx["home"], "away": fx["away"], "round": fx["round"],
                "predicted": label[pred_oc], "pred_score": pred["expected"]["most_likely_score"],
                "actual": f"{gh}-{ga}", "result": label[actual_oc],
                "confidence": probs[pred_oc], "hit": hit, "score_hit": score_hit,
            })
            ch, ca = ratings.canonical(fx["home"]), ratings.canonical(fx["away"])
            nh, na = elo.update(r.get(ch, ratings.DEFAULT_RATING),
                                r.get(ca, ratings.DEFAULT_RATING), gh, ga, neutral=True)
            r[ch], r[ca] = nh, na
        if n == 0:
            return {"summary": {"matches": 0}, "log": []}
        return {
            "summary": {
                "matches": n,
                "result_accuracy": _pct(r1 / n),
                "score_accuracy": _pct(sc / n),
                "over_under_accuracy": _pct(ou / n),
                "btts_accuracy": _pct(bt / n),
                "avg_confidence": _pct(conf_sum / n),
            },
            "log": log[::-1],
        }
    return cache.get_or_fetch("accuracy", build, ttl_minutes=10)
