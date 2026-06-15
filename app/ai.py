"""Panini AI helper — a chat assistant grounded in the model's own predictions.

Uses the Anthropic API (Claude Opus 4.8). The model is given the current
fixtures, win probabilities and betting tips as context, so it answers about
real matches rather than guessing. Enabled only when ANTHROPIC_API_KEY is set;
otherwise the endpoint returns a friendly "not configured" message.
"""
from __future__ import annotations

import os

from . import store
from .data import cache, sources
from .models import poisson, ratings, tips

MODEL = "claude-opus-4-8"

SYSTEM = (
    "You are Panini, a friendly and sharp football betting assistant for the "
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
