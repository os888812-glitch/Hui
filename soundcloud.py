from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path
from typing import Any

from yt_dlp import YoutubeDL
from yt_dlp.extractor.soundcloud import SoundcloudBaseIE

from models import Track


class SoundCloudClient:
    def __init__(self, search_limit: int = 10) -> None:
        self.search_limit = search_limit

    async def search(self, query: str) -> list[Track]:
        return await asyncio.to_thread(self._search_sync, query)

    async def search_section(self, query: str, section: str) -> list[Track]:
        return await asyncio.to_thread(self._search_section_sync, query, section)

    async def resolve(self, url: str) -> Track:
        return await asyncio.to_thread(self._resolve_sync, url)

    async def download(self, track: Track, downloads_dir: Path) -> Path:
        return await asyncio.to_thread(self._download_sync, track, downloads_dir)

    def _search_sync(self, query: str) -> list[Track]:
        if _looks_like_url(query):
            return [self._resolve_sync(query)]
        options = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "extract_flat": False,
            "noplaylist": True,
        }
        with YoutubeDL(options) as ydl:
            info = ydl.extract_info(f"scsearch{self.search_limit}:{query}", download=False)
            entries = (info or {}).get("entries") or []
            return [_track_from_info(entry) for entry in entries if entry]

    def _search_section_sync(self, query: str, section: str) -> list[Track]:
        if section == "songs":
            return self._search_sync(query)
        endpoint = {
            "albums": "search/albums",
            "playlists": "search/playlists",
        }.get(section)
        if not endpoint:
            return []
        options = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "extract_flat": True,
        }
        with YoutubeDL(options) as ydl:
            ie = SoundcloudBaseIE(ydl)
            ie._initialize_pre_login()
            data = ie._call_api(
                f"https://api-v2.soundcloud.com/{endpoint}",
                query,
                f"Downloading SoundCloud {section}",
                query={
                    "q": query,
                    "limit": self.search_limit,
                    "offset": 0,
                    "linked_partitioning": 1,
                },
                headers=ie._HEADERS,
            )
            entries = (data or {}).get("collection") or []
            return [_collection_from_info(entry) for entry in entries if entry]

    def _resolve_sync(self, url: str) -> Track:
        options = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "noplaylist": True,
        }
        with YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=False)
            return _track_from_info(info)

    def _download_sync(self, track: Track, downloads_dir: Path) -> Path:
        downloads_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=downloads_dir) as temp_dir:
            output = str(Path(temp_dir) / "%(id)s.%(ext)s")
            options = {
                "format": "bestaudio/best",
                "outtmpl": output,
                "quiet": True,
                "no_warnings": True,
                "noplaylist": True,
            }
            with YoutubeDL(options) as ydl:
                info = ydl.extract_info(track.url, download=True)
                filename = Path(ydl.prepare_filename(info))
                final_path = downloads_dir / filename.name
                filename.replace(final_path)
                return final_path


def _track_from_info(info: dict[str, Any] | None) -> Track:
    if not info:
        raise ValueError("SoundCloud returned an empty response.")
    title = info.get("title") or "Untitled"
    artist = info.get("uploader") or info.get("creator") or info.get("channel") or ""
    url = info.get("webpage_url") or info.get("url")
    if not url:
        raise ValueError("SoundCloud result has no URL.")
    return Track(
        title=str(title),
        artist=str(artist),
        url=str(url),
        duration=_safe_int(info.get("duration")),
        thumbnail=info.get("thumbnail"),
        source_id=str(info.get("id")) if info.get("id") else None,
    )


def _collection_from_info(info: dict[str, Any]) -> Track:
    user = info.get("user") or {}
    url = info.get("permalink_url") or info.get("uri")
    if not url:
        raise ValueError("SoundCloud collection result has no URL.")
    duration_ms = _safe_int(info.get("duration"))
    duration = duration_ms // 1000 if duration_ms else None
    source_id = info.get("id") or info.get("urn") or url
    return Track(
        title=str(info.get("title") or "Untitled"),
        artist=str(user.get("username") or info.get("user_id") or ""),
        url=str(url),
        duration=duration,
        thumbnail=info.get("artwork_url"),
        source_id=str(source_id),
    )


def _safe_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _looks_like_url(value: str) -> bool:
    lower = value.strip().lower()
    return lower.startswith("http://") or lower.startswith("https://")
    
