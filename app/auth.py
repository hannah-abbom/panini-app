"""Minimal single-user authentication.

This site is meant for one person, so we keep it simple: a single password
set in the .env file. On a correct password we hand out a signed, expiring
cookie (HMAC over an expiry timestamp). No database, no user table.
"""
from __future__ import annotations

import hashlib
import hmac
import time

from fastapi import Cookie, HTTPException, status

from .config import settings

COOKIE_NAME = "panini_session"
SESSION_TTL_SECONDS = 60 * 60 * 24 * 14  # 14 days


def _sign(payload: str) -> str:
    return hmac.new(
        settings.secret_key.encode(), payload.encode(), hashlib.sha256
    ).hexdigest()


def check_password(password: str) -> bool:
    """Constant-time comparison against the configured password."""
    return hmac.compare_digest(password, settings.access_password)


def issue_token() -> str:
    expiry = str(int(time.time()) + SESSION_TTL_SECONDS)
    return f"{expiry}.{_sign(expiry)}"


def token_is_valid(token: str | None) -> bool:
    if not token or "." not in token:
        return False
    expiry, sig = token.split(".", 1)
    if not hmac.compare_digest(sig, _sign(expiry)):
        return False
    try:
        return int(expiry) > time.time()
    except ValueError:
        return False


def require_auth(panini_session: str | None = Cookie(default=None)) -> bool:
    """FastAPI dependency that rejects unauthenticated API requests."""
    if not token_is_valid(panini_session):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )
    return True
