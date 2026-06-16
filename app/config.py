"""Application configuration loaded from environment / .env file."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class Settings:
    """Runtime settings. Values come from the environment (.env)."""

    access_password: str = os.getenv("ACCESS_PASSWORD", "changeme")
    secret_key: str = os.getenv("SECRET_KEY", "dev-insecure-secret-change-me")
    # Login is OFF by default (personal tool). Set REQUIRE_AUTH=true to enable.
    require_auth: bool = os.getenv("REQUIRE_AUTH", "").strip().lower() in (
        "1", "true", "yes", "on")
    cache_ttl_minutes: int = int(os.getenv("CACHE_TTL_MINUTES", "30"))
    cache_dir: Path = BASE_DIR / ".cache"
    static_dir: Path = BASE_DIR / "app" / "static"

    def __init__(self) -> None:
        self.cache_dir.mkdir(exist_ok=True)


settings = Settings()
