# ⚽ Panini — personal World Cup prediction model

A private, password-protected web app that predicts FIFA World Cup 2026 matches
to help you make better **pronostics**. It turns team strength ratings into goal
probabilities and reads every common betting market off the result — plus a
value/Kelly calculator so you can compare the model to a bookmaker's odds.

> Built for one user (you). It is a **decision-support tool**, not a guarantee.
> No model beats the bookmakers reliably — bet responsibly and only what you can
> afford to lose.

## What it does

- **Fixtures view** — upcoming World Cup matches, each with win/draw/win
  probabilities, the most likely scoreline, and expected total goals.
- **Full match markets** — tap any match for:
  - 1X2 and double chance (1X / 12 / X2)
  - Over/Under 1.5, 2.5, 3.5 goals
  - Both teams to score
  - Most likely correct scores
  - "Fair odds" implied by the model
- **Custom matchup** — pick any two teams (e.g. a knockout-round what-if), with
  an optional home-advantage toggle for the host nations.
- **Value calculator** — paste the model's probability and the bookmaker's
  decimal odds; get your edge and a Kelly-criterion stake.

## How the model works

1. **Elo ratings** (`app/models/ratings.py`, `elo.py`) — every nation has a
   World-Football-Elo style strength rating. The engine can update them as real
   results come in.
2. **Expected goals** — the Elo gap becomes an expected goal *supremacy* and an
   expected *total*, split into per-team scoring rates.
3. **Dixon–Coles / Poisson** (`app/models/poisson.py`) — those rates build the
   full scoreline matrix, with the Dixon–Coles low-score correction. Every
   market is read directly off that matrix.

## Data sources

Fixtures and form are pulled from **FotMob** and **SofaScore**'s public JSON
endpoints (`app/data/`), with a built-in **sample fixture set** so the app
always works even when those are unreachable.

> ⚠️ These providers have **no official public API**. The endpoints are
> undocumented, can change or rate-limit without notice, and are subject to each
> site's **terms of service**. Requests are cached and kept low-volume, and
> every call fails gracefully to the next source. Use this for personal,
> non-commercial purposes and check each provider's terms before relying on it.

## Running it

```bash
cp .env.example .env       # then edit ACCESS_PASSWORD and SECRET_KEY
./run.sh                   # first run creates a venv and installs deps
```

Then open <http://127.0.0.1:8000> and log in with your password.

Generate a strong secret key with:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### Manual setup (instead of `run.sh`)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env       # edit it
uvicorn app.main:app --reload
```

## Configuration (`.env`)

| Variable             | Meaning                                            |
| -------------------- | -------------------------------------------------- |
| `ACCESS_PASSWORD`    | The password you type to log in.                   |
| `SECRET_KEY`         | Long random string used to sign your login cookie. |
| `CACHE_TTL_MINUTES`  | How long live data is cached before refetching.    |

## Project layout

```
app/
  main.py            FastAPI routes (pages + JSON API)
  auth.py            single-user password + signed cookie
  config.py          .env settings
  models/
    ratings.py       seed Elo ratings + name aliases
    elo.py           Elo expected score + result updates
    poisson.py       Dixon–Coles/Poisson engine + value/Kelly
  data/
    fotmob.py        FotMob client (defensive)
    sofascore.py     SofaScore client (defensive)
    sources.py       source aggregation + fallback chain
    cache.py         JSON file cache
    sample_fixtures.py  offline fallback fixtures
  static/            login + single-page UI (vanilla JS, no build step)
```

## Tuning the model

- Edit team strengths in `app/models/ratings.py`.
- Adjust `BASE_TOTAL_GOALS`, `ELO_PER_GOAL`, `DIXON_COLES_RHO`, and
  `HOME_ADVANTAGE` in `app/models/poisson.py` / `elo.py` to taste.
