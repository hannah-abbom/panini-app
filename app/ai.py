"""Panini AI helper — a chat assistant grounded in the model's own predictions.

Uses the Anthropic API (Claude Opus 4.8). The model is given the current
fixtures, win probabilities and betting tips as context, so it answers about
real matches rather than guessing. Enabled only when ANTHROPIC_API_KEY is set;
otherwise the endpoint returns a friendly "not configured" message.
"""
from __future__ import annotations

import os
import re

from . import store
from .data import cache, sources
from .models import poisson, ratings, tips

MODEL = "claude-opus-4-8"

SYSTEM = (
    "You are Predi AI, a friendly and sharp football betting assistant for the "
    "2026 FIFA World Cup. You help the user understand the model's predictions "
    "and betting tips, compare matchups, and decide what to bet on.\n\n"
    "Rules:\n"
    "- Use ONLY the model data below as your source of truth for probabilities, "
    "expected goals, tips and results. Do not invent odds, stats or scores.\n"
    "- Be concise and direct. Lead with the answer, then a short reason.\n"
    "- When you suggest a bet, make clear it's a model-based estimate, not a "
    "guarantee, and remind the user to bet responsibly when relevant.\n"
    "- Respond only with your final answer — no step-by-step reasoning.\n\n"
    "CURRENT MODEL DATA:\n{context}"
)


def ai_enabled() -> bool:
    return bool(os.getenv("ANTHROPIC_API_KEY"))


def _wc_elo(name: str) -> float:
    base = store.rating_for(name)
    return base + ratings.HOST_BONUS if ratings.is_host(name) else base


def _build_context() -> str:
    def build() -> str:
        data = sources.get_fixtures()
        lines = []
        for fx in data["fixtures"]:
            if fx.get("status") == "finished":
                lines.append(f"{fx['round']}: {fx['home']} {fx.get('score','')} "
                             f"{fx['away']} (FULL TIME)")
                continue
            pred = poisson.predict(fx["home"], fx["away"],
                                   _wc_elo(fx["home"]), _wc_elo(fx["away"])).to_dict()
            t = tips.best_tip(pred)
            r, st = pred["result"], pred["stats"]
            lines.append(
                f"{fx['round']} {fx['utc_date'][:10]}: {fx['home']} vs {fx['away']} "
                f"— win% {r['home_win']}/{r['draw']}/{r['away_win']}, "
                f"xG {pred['expected']['goals_home']}-{pred['expected']['goals_away']}, "
                f"O2.5 {pred['goals']['over_under']['2.5']['over']}%, "
                f"BTTS {pred['goals']['btts']['yes']}%, "
                f"corners {st['corners']['total']}, cards {st['cards']['total']}, "
                f"TIP: {t['selection']} @ {t['odds']} ({t['confidence']})")
        return "\n".join(lines)

    return cache.get_or_fetch("ai_context", build, ttl_minutes=15)


# ---- Local (no-key) responder: answers straight from the model ------------

def _structured() -> list[dict]:
    def build() -> list[dict]:
        data = sources.get_fixtures()
        rows = []
        for fx in data["fixtures"]:
            pred = poisson.predict(fx["home"], fx["away"],
                                   _wc_elo(fx["home"]), _wc_elo(fx["away"])).to_dict()
            rows.append({
                "home": fx["home"], "away": fx["away"], "round": fx["round"],
                "status": fx.get("status", "upcoming"), "score": fx.get("score"),
                "date": fx["utc_date"][:10], "r": pred["result"],
                "goals": pred["goals"], "stats": pred["stats"],
                "exp": pred["expected"], "tip": tips.best_tip(pred),
            })
        return rows
    return cache.get_or_fetch("ai_structured", build, ttl_minutes=15)


def _team_names() -> list[str]:
    names = set(ratings.SEED_RATINGS) | set(ratings.ALIASES) | {"USA"}
    return [n for n in names if len(n) >= 3]


def _teams_in(text: str) -> list[str]:
    low = text.lower()
    found: list[str] = []
    for name in sorted(_team_names(), key=len, reverse=True):
        if re.search(r"\b" + re.escape(name.lower()) + r"\b", low):
            c = ratings.canonical(name)
            if c not in found:
                found.append(c)
    return found


def _answer_match(r: dict, focus: str | None = None) -> str:
    if r["status"] == "finished":
        return f"{r['home']} {r['score']} {r['away']} — full time."
    res, tip, exp, g, st = r["r"], r["tip"], r["exp"], r["goals"], r["stats"]
    live = " (LIVE now: " + str(r["score"]) + ")" if r["status"] == "live" else ""
    return "\n".join([
        f"{r['home']} vs {r['away']}{live}:",
        f"• Win chance — {r['home']} {res['home_win']}%, draw {res['draw']}%, {r['away']} {res['away_win']}%",
        f"• Likely score {exp['most_likely_score']}, ~{exp['total']} goals · over 2.5 {g['over_under']['2.5']['over']}% · BTTS {g['btts']['yes']}%",
        f"• Corners ~{st['corners']['total']} · cards ~{st['cards']['total']}",
        f"🎯 Best bet: {tip['selection']} @ {tip['odds']} ({tip['confidence']} confidence). Model estimate — bet responsibly.",
    ])


def _top_tips(rows, key=None, n=5) -> str:
    up = [r for r in rows if r["status"] not in ("finished", "live")]
    if key:
        up.sort(key=lambda r: -key(r))
    else:
        up.sort(key=lambda r: (-r["tip"]["stars"], -r["tip"]["prob"]))
    lines = ["🎯 Top picks right now:"]
    for r in up[:n]:
        lines.append(f"• {r['home']} v {r['away']} — {r['tip']['selection']} @ {r['tip']['odds']}")
    lines.append("\nModel estimates only — bet responsibly.")
    return "\n".join(lines)


def local_answer(message: str) -> str:
    """Rule-based answer from the model — works with no API key."""
    low = (message or "").lower()
    rows = _structured()
    if not low.strip():
        return "Hi! Ask me about any match (e.g. \"Brazil vs Morocco\") or say \"best bets\"."

    if "live" in low:
        liv = [r for r in rows if r["status"] == "live"]
        if liv:
            return "Live now:\n" + "\n".join(f"• {r['home']} {r['score']} {r['away']}" for r in liv)
        return "No World Cup games are live right now — check the Matches tab for kickoff times."

    if any(k in low for k in ("best bet", "best bets", "bet of the day", "top tip",
                              "best tip", "good bet", "what should i bet", "tips")):
        return _top_tips(rows)
    if "corner" in low:
        return _top_tips(rows, key=lambda r: r["stats"]["corners"]["total"])
    if "card" in low:
        return _top_tips(rows, key=lambda r: r["stats"]["cards"]["total"])
    if "over" in low or "goals" in low:
        return _top_tips(rows, key=lambda r: r["goals"]["over_under"]["2.5"]["over"])

    teams = _teams_in(message)
    if len(teams) >= 2:
        for r in rows:
            if {ratings.canonical(r["home"]), ratings.canonical(r["away"])} == {teams[0], teams[1]}:
                return _answer_match(r)
        h, a = teams[0], teams[1]
        pred = poisson.predict(h, a, _wc_elo(h), _wc_elo(a)).to_dict()
        return _answer_match({"home": h, "away": a, "status": "upcoming",
                              "r": pred["result"], "goals": pred["goals"],
                              "stats": pred["stats"], "exp": pred["expected"],
                              "tip": tips.best_tip(pred)})
    if len(teams) == 1:
        for r in rows:
            if teams[0] in (ratings.canonical(r["home"]), ratings.canonical(r["away"])):
                return _answer_match(r)
        return f"I couldn't find a fixture for {teams[0]}. Try two teams, e.g. \"Spain vs Cape Verde\"."

    return ("I can talk through any match or the best bets. Try \"best bets\", "
            "\"Brazil vs Morocco\", or \"who wins Spain's game?\"\n\n" + _top_tips(rows, n=3))


def chat(history: list[dict]) -> str:
    import anthropic

    client = anthropic.Anthropic()
    system = SYSTEM.format(context=_build_context())
    msgs = [{"role": m["role"], "content": m["content"]}
            for m in history if m.get("content") and m.get("role") in ("user", "assistant")][-12:]
    if not msgs:
        return "Ask me anything about the World Cup matches or the model's tips!"
    resp = client.messages.create(model=MODEL, max_tokens=1024, system=system, messages=msgs)
    return "".join(b.text for b in resp.content if b.type == "text").strip()
