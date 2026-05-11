from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field

from .models import Track


@dataclass
class CachedSearch:
    query: str
    tracks: list[Track]
    created_at: float
    sections: dict[str, list[Track]] = field(default_factory=dict)


class ResultCache:
    def __init__(self, ttl_seconds: int = 20 * 60) -> None:
        self.ttl_seconds = ttl_seconds
        self._searches: dict[str, CachedSearch] = {}
        self._tracks: dict[str, tuple[Track, float]] = {}

    def put_search(self, query: str, tracks: list[Track]) -> str:
        self._prune()
        key = uuid.uuid4().hex[:12]
        now = time.time()
        self._searches[key] = CachedSearch(query=query, tracks=tracks, created_at=now)
        for track in tracks:
            self.put_track(track)
        return key

    def put_track(self, track: Track) -> str:
        self._prune()
        key = self._track_key(track)
        self._tracks[key] = (track, time.time())
        return key

    def get_search(self, key: str) -> CachedSearch | None:
        self._prune()
        return self._searches.get(key)

    def put_section(self, key: str, section: str, tracks: list[Track]) -> None:
        self._prune()
        search = self._searches.get(key)
        if search:
            search.sections[section] = tracks

    def get_track(self, key: str) -> Track | None:
        self._prune()
        item = self._tracks.get(key)
        return item[0] if item else None

    @staticmethod
    def _track_key(track: Track) -> str:
        base = track.source_id or track.url or track.title
        return uuid.uuid5(uuid.NAMESPACE_URL, base).hex[:16]

    def _prune(self) -> None:
        now = time.time()
        cutoff = now - self.ttl_seconds
        self._searches = {
            key: value for key, value in self._searches.items() if value.created_at >= cutoff
        }
        self._tracks = {
            key: value for key, value in self._tracks.items() if value[1] >= cutoff
        }
