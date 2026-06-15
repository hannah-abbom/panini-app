"""Tiny JSON file cache so we are not hammering external providers."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Callable

from ..config import settings


def _path(key: str) -> Path:
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in key)
    return settings.cache_dir / f"{safe}.json"


def get_or_fetch(key: str, fetch: Callable[[], Any],
                 ttl_minutes: int | None = None) -> Any:
    """Return cached value for `key`, else call `fetch()` and cache it.

    If `fetch()` raises (e.g. provider down / blocked), fall back to any stale
    cached value rather than failing the request.
    """
    ttl = (ttl_minutes if ttl_minutes is not None
           else settings.cache_ttl_minutes) * 60
    path = _path(key)
    cached = None
    if path.exists():
        try:
            cached = json.loads(path.read_text())
            if time.time() - cached["_ts"] < ttl:
                return cached["data"]
        except (json.JSONDecodeError, KeyError):
            cached = None

    try:
        data = fetch()
        path.write_text(json.dumps({"_ts": time.time(), "data": data}))
        return data
    except Exception:
        if cached is not None:
            return cached["data"]
        raise
