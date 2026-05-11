from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Track:
    title: str
    artist: str
    url: str
    duration: int | None = None
    thumbnail: str | None = None
    source_id: str | None = None

    @property
    def display_artist(self) -> str:
        return self.artist or "unknown"
