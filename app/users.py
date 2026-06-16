"""User authentication — password hashing + signed session tokens.

Accounts are optional: the app works without logging in; an account just unlocks
favourites, saved picks and personalised daily picks. Passwords are stored as
PBKDF2-HMAC-SHA256 hashes; sessions are stateless HMAC-signed cookies.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import time

from .config import settings

SESSION_TTL = 60 * 60 * 24 * 30   # 30 days
_ITER = 120_000


def hash_pw(password: str, salt: str | None = None) -> str:
    salt = salt or os.urandom(16).hex()
    h = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), _ITER).hex()
    return f"{salt}${h}"


def verify_pw(password: str, stored: str) -> bool:
    try:
        salt, h = stored.split("$", 1)
    except ValueError:
        return False
    test = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), _ITER).hex()
    return hmac.compare_digest(test, h)


def make_token(uid: int) -> str:
    payload = f"{uid}.{int(time.time()) + SESSION_TTL}"
    sig = hmac.new(settings.secret_key.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}.{sig}"


def user_from_token(token: str | None):
    if not token or token.count(".") != 2:
        return None
    uid, exp, sig = token.split(".")
    payload = f"{uid}.{exp}"
    good = hmac.new(settings.secret_key.encode(), payload.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, good):
        return None
    try:
        if int(exp) < time.time():
            return None
        from . import db
        return db.get_user_by_id(int(uid))
    except (ValueError, TypeError):
        return None
