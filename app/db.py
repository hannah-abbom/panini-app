"""SQLite storage for user accounts, favourites and saved picks.

Lightweight, zero-dependency persistence. Lives in .data/app.db. Note: on an
ephemeral host (e.g. Render free tier) this resets on redeploy — mount a
persistent disk at /app/.data or point at Postgres for production durability.
"""
from __future__ import annotations

import sqlite3
import threading
import time

from .config import BASE_DIR

DB_PATH = BASE_DIR / ".data" / "app.db"
_lock = threading.Lock()


def _conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(exist_ok=True)
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def init() -> None:
    with _lock, _conn() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT UNIQUE NOT NULL,
            pw TEXT NOT NULL, plan TEXT NOT NULL DEFAULT 'free', created REAL)""")
        c.execute("""CREATE TABLE IF NOT EXISTS favourites (
            user_id INTEGER, team TEXT, UNIQUE(user_id, team))""")
        c.execute("""CREATE TABLE IF NOT EXISTS saved (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, match TEXT,
            selection TEXT, odds REAL, created REAL)""")


def create_user(email: str, pw: str) -> int:
    with _lock, _conn() as c:
        cur = c.execute("INSERT INTO users (email, pw, created) VALUES (?,?,?)",
                        (email, pw, time.time()))
        return cur.lastrowid


def get_user_by_email(email: str):
    with _conn() as c:
        return c.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()


def get_user_by_id(uid: int):
    with _conn() as c:
        return c.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()


def set_plan(uid: int, plan: str) -> None:
    with _lock, _conn() as c:
        c.execute("UPDATE users SET plan=? WHERE id=?", (plan, uid))


def list_favs(uid: int) -> list[str]:
    with _conn() as c:
        return [r["team"] for r in c.execute(
            "SELECT team FROM favourites WHERE user_id=? ORDER BY team", (uid,))]


def add_fav(uid: int, team: str) -> None:
    with _lock, _conn() as c:
        c.execute("INSERT OR IGNORE INTO favourites (user_id, team) VALUES (?,?)", (uid, team))


def remove_fav(uid: int, team: str) -> None:
    with _lock, _conn() as c:
        c.execute("DELETE FROM favourites WHERE user_id=? AND team=?", (uid, team))


def list_saved(uid: int) -> list[dict]:
    with _conn() as c:
        return [dict(r) for r in c.execute(
            "SELECT id, match, selection, odds FROM saved WHERE user_id=? ORDER BY id DESC", (uid,))]


def add_saved(uid: int, match: str, selection: str, odds: float) -> None:
    with _lock, _conn() as c:
        c.execute("INSERT INTO saved (user_id, match, selection, odds, created) VALUES (?,?,?,?,?)",
                  (uid, match, selection, odds, time.time()))


def remove_saved(uid: int, pick_id: int) -> None:
    with _lock, _conn() as c:
        c.execute("DELETE FROM saved WHERE user_id=? AND id=?", (uid, pick_id))


init()
