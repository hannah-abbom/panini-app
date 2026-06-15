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
                "picks": tips.top_picks(pred, 3),
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


def _upcoming(rows):
    return [r for r in rows if r["status"] not in ("finished", "live")]


def _answer_match(r: dict) -> str:
    if r["status"] == "finished":
        return f"**{r['home']} {r['score']} {r['away']}** — full time."
    res, exp, g, st = r["r"], r["exp"], r["goals"], r["stats"]
    live = f" (🔴 LIVE: {r['score']})" if r["status"] == "live" else ""
    picks = r.get("picks", [r["tip"]])
    lines = [
        f"**{r['home']} vs {r['away']}**{live}",
        f"• Win chance — {r['home']} **{res['home_win']}%**, draw {res['draw']}%, {r['away']} **{res['away_win']}%**",
        f"• Likely score **{exp['most_likely_score']}** · ~{exp['total']} goals · over 2.5 {g['over_under']['2.5']['over']}% · BTTS {g['btts']['yes']}%",
        f"• Corners ~{st['corners']['total']} · cards ~{st['cards']['total']}",
        "🎯 Best bets:",
    ]
    lines += [f"• **{p['selection']}** @ {p['odds']} ({p['prob']}%)" for p in picks[:3]]
    lines.append("\nModel estimates — bet responsibly.")
    return "\n".join(lines)


def _top_tips(rows, key=None, n=5, title="🎯 Top picks right now:") -> str:
    up = _upcoming(rows)
    up.sort(key=key if key else (lambda r: (-r["tip"]["stars"], -r["tip"]["prob"])))
    lines = [title]
    for r in up[:n]:
        lines.append(f"• {r['home']} v {r['away']} — **{r['tip']['selection']}** @ {r['tip']['odds']}")
    lines.append("\nModel estimates only — bet responsibly.")
    return "\n".join(lines)


def _all_picks(rows):
    out = []
    for r in _upcoming(rows):
        for p in r.get("picks", [r["tip"]]):
            out.append((r, p))
    return out


def _pick_list(title, items, n=6) -> str:
    lines, seen = [title], set()
    for r, p in items:
        k = (r["home"], r["away"], p["selection"])
        if k in seen:
            continue
        seen.add(k)
        lines.append(f"• {r['home']} v {r['away']} — **{p['selection']}** @ {p['odds']} ({p['prob']}%)")
        if len(seen) >= n:
            break
    lines.append("\nModel estimates — bet responsibly.")
    return "\n".join(lines)


def _acca(rows, n) -> str:
    n = max(2, min(6, n or 3))
    picks = sorted(_upcoming(rows), key=lambda r: (-r["tip"]["stars"], -r["tip"]["prob"]))[:n]
    comb = 1.0
    for r in picks:
        comb *= r["tip"]["odds"]
    comb = round(comb, 2)
    lines = [f"Here's a **{len(picks)}-fold accumulator**:"]
    lines += [f"• {r['home']} v {r['away']} — **{r['tip']['selection']}** @ {r['tip']['odds']}" for r in picks]
    lines.append(f"\nCombined odds **{comb}** — a £10 stake returns **£{round(comb * 10, 2)}**.")
    lines.append("Build it leg-by-leg on the Tips tab. More legs = bigger payout, lower chance. Bet responsibly.")
    return "\n".join(lines)


def _group(rows, letter) -> str:
    g = f"Group {letter.upper()}"
    grows = [r for r in rows if r["round"] == g]
    if not grows:
        return f"I couldn't find {g}."
    teams = sorted({r["home"] for r in grows} | {r["away"] for r in grows},
                   key=lambda t: -store.rating_for(t))
    lines = [f"**{g}** — model order:"]
    lines += [f"{i}. {t}" for i, t in enumerate(teams, 1)]
    up = _upcoming(grows)
    if up:
        lines.append("\nUpcoming picks:")
        lines += [f"• {r['home']} v {r['away']} — **{r['tip']['selection']}** @ {r['tip']['odds']}" for r in up[:6]]
    return "\n".join(lines)


def _favourites() -> str:
    rated = sorted(store.all_ratings().items(), key=lambda kv: -kv[1])[:6]
    lines = ["🏆 Title favourites by the model:"]
    lines += [f"{i}. {t} ({round(e)})" for i, (t, e) in enumerate(rated, 1)]
    return "\n".join(lines)


_HELP = ("I'm **Predi AI** ⚽ — here's what I can do:\n"
         "• **best bets** — the strongest tips right now\n"
         "• **build me an acca** (or \"4-fold\") — a ready accumulator\n"
         "• **value picks** or **safest picks**\n"
         "• **Brazil vs Morocco** — a full match prediction\n"
         "• **most corners / cards / goals**\n"
         "• **Group H** — group order + picks\n"
         "• **who will win the World Cup**\n"
         "Just ask away!")


def local_answer(message: str) -> str:
    """Rule-based answer from the model — works with no API key."""
    msg = message or ""
    low = msg.lower().strip()
    rows = _structured()
    if not low:
        return _HELP
    if low in ("hi", "hello", "hey", "yo", "sup") or low.startswith(("hi ", "hello", "hey")):
        return "Hey! ⚽ I'm **Predi AI**. Ask me for the **best bets**, a prediction like **Brazil vs Morocco**, or say **build me an acca**."
    if "thank" in low:
        return "Anytime — good luck! 🍀 Ask me for more whenever you like."
    if "help" in low or "what can you" in low:
        return _HELP

    if "live" in low:
        liv = [r for r in rows if r["status"] == "live"]
        if liv:
            return "🔴 Live now:\n" + "\n".join(f"• {r['home']} **{r['score']}** {r['away']}" for r in liv)
        return "No World Cup games are live right now — check the Matches tab for kickoff times."

    if any(k in low for k in ("acca", "accumulator", "parlay", "fold", "multi", "combo")):
        m = re.search(r"\b(\d+)\b", low)
        return _acca(rows, int(m.group(1)) if m else 3)
    if any(k in low for k in ("value", "longshot", "long shot", "upset", "underdog")):
        items = sorted([(r, p) for (r, p) in _all_picks(rows) if p["odds"] >= 1.7],
                       key=lambda rp: -rp[1]["prob"])
        return _pick_list("💎 Value picks (bigger odds the model still rates):", items)
    if any(k in low for k in ("safe", "banker", "sure", "confident", "most likely")):
        items = sorted(_all_picks(rows), key=lambda rp: -rp[1]["prob"])
        return _pick_list("🛡️ Safest picks (highest model confidence):", items)
    if any(k in low for k in ("win the world cup", "champion", "favourite", "favorite",
                              "win it all", "lift the", "tournament winner")):
        return _favourites()

    gm = re.search(r"group ([a-l])\b", low)
    if gm:
        return _group(rows, gm.group(1))

    if any(k in low for k in ("best bet", "best bets", "bet of the day", "top tip",
                              "best tip", "good bet", "what should i bet", "tips", "recommend")):
        return _top_tips(rows)
    if "corner" in low:
        return _top_tips(rows, key=lambda r: -r["stats"]["corners"]["total"], title="⛳ Most corners expected:")
    if "card" in low:
        return _top_tips(rows, key=lambda r: -r["stats"]["cards"]["total"], title="🟨 Most cards expected:")
    if "over" in low or "goal" in low:
        return _top_tips(rows, key=lambda r: -r["goals"]["over_under"]["2.5"]["over"], title="⚽ Most goals expected:")

    teams = _teams_in(msg)
    if len(teams) >= 2:
        for r in rows:
            if {ratings.canonical(r["home"]), ratings.canonical(r["away"])} == {teams[0], teams[1]}:
                return _answer_match(r)
        h, a = teams[0], teams[1]
        pred = poisson.predict(h, a, _wc_elo(h), _wc_elo(a)).to_dict()
        return _answer_match({"home": h, "away": a, "status": "upcoming",
                              "r": pred["result"], "goals": pred["goals"],
                              "stats": pred["stats"], "exp": pred["expected"],
                              "tip": tips.best_tip(pred), "picks": tips.top_picks(pred, 3)})
    if len(teams) == 1:
        for r in rows:
            if teams[0] in (ratings.canonical(r["home"]), ratings.canonical(r["away"])):
                return _answer_match(r)
        return f"I couldn't find a fixture for {teams[0]}. Try two teams, e.g. \"Spain vs Cape Verde\"."

    return "I didn't quite catch that. " + _HELP


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
