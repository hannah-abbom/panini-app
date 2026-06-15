# Deploying Panini (with HTTPS)

Panini is a single FastAPI service. Below are three ways to run it; all of them
keep your Elo ratings and result log on a persistent volume.

## Option A — Docker + Caddy (recommended, automatic HTTPS)

This runs the app behind [Caddy](https://caddyserver.com/), which provisions and
renews free Let's Encrypt certificates for you.

1. **Get a server** (any small VPS) and point a domain's `A` record at its IP.
2. **Configure:**
   ```bash
   cp .env.example .env          # set ACCESS_PASSWORD and a strong SECRET_KEY
   # edit Caddyfile: replace panini.example.com with your domain + email
   ```
   Generate a secret key:
   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```
3. **Run:**
   ```bash
   docker compose up -d --build
   ```
4. Open `https://your-domain` and log in. Certificates are issued on first hit.

Remove the `ports: 8000:8000` line from `docker-compose.yml` in production so
the app is only reachable through Caddy (HTTPS).

## Option B — One container, no domain (quick test)

```bash
docker build -t panini .
docker run -p 8000:8000 --env-file .env -v panini-data:/app/.data panini
```
Reach it at <http://localhost:8000>. (No HTTPS — local use only.)

## Option C — Platform-as-a-Service (Render, Railway, Fly.io, etc.)

These give you HTTPS automatically on a provided subdomain.

- **Start command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- **Build:** `pip install -r requirements.txt`
- **Environment variables:** `ACCESS_PASSWORD`, `SECRET_KEY`, `CACHE_TTL_MINUTES`
- **Persistent disk:** mount one at `/app/.data` so ratings survive deploys.

A `Procfile` is included for platforms that use it.

## Notes on data sources in production

FotMob and SofaScore may rate-limit or block datacenter IP ranges more
aggressively than home connections. If live fixtures stop loading, the app
automatically falls back to the bundled sample data and any results you've
recorded — it never goes down because a provider did. Keep request volume
modest and respect each provider's terms of service.

## Security reminders

- Always set a strong, unique `SECRET_KEY` and `ACCESS_PASSWORD`.
- Only expose the app over HTTPS (Option A or C). The login cookie is sent on
  every request.
- This app is intended for a single user (you). Don't share the URL/password.
