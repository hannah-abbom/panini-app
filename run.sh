#!/usr/bin/env bash
set -euo pipefail

# Create / activate a virtual environment and install deps on first run.
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
  ./.venv/bin/pip install --upgrade pip
  ./.venv/bin/pip install -r requirements.txt
fi

if [ ! -f ".env" ]; then
  echo "No .env found - copying .env.example to .env (edit it to set your password)."
  cp .env.example .env
fi

exec ./.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
