from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ASSETS_DIR = PROJECT_ROOT / "assets"


def _bool_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    bot_token: str
    sticker_set_name: str = "HeartBalloons"
    sticker_index: int = 5
    fallback_sticker_path: Path = ASSETS_DIR / "heartballoons_05.webp"
    ad_contact: str = "loaditbot@proton.me"
    allow_audio_downloads: bool = False
    max_audio_mb: int = 45
    search_limit: int = 10
    results_per_page: int = 5
    downloads_dir: Path = PROJECT_ROOT / "downloads"

    @property
    def max_audio_bytes(self) -> int:
        return self.max_audio_mb * 1024 * 1024


def load_settings() -> Settings:
    load_dotenv(PROJECT_ROOT / ".env", encoding="utf-8-sig")
    token = os.getenv("BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("BOT_TOKEN is not set. Copy .env.example to .env and add your Telegram bot token.")

    return Settings(
        bot_token=token,
        sticker_set_name=os.getenv("STICKER_SET_NAME", "HeartBalloons").strip() or "HeartBalloons",
        sticker_index=max(1, _int_env("STICKER_INDEX", 5)),
        ad_contact=os.getenv("AD_CONTACT", "loaditbot@proton.me").strip() or "loaditbot@proton.me",
        allow_audio_downloads=_bool_env("ALLOW_AUDIO_DOWNLOADS", False),
        max_audio_mb=max(1, _int_env("MAX_AUDIO_MB", 45)),
        search_limit=max(1, _int_env("SEARCH_LIMIT", 10)),
        results_per_page=max(1, _int_env("RESULTS_PER_PAGE", 5)),
    )
