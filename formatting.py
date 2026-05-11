from __future__ import annotations

from html import escape

from collections.abc import Callable

from .models import Track


def format_duration(seconds: int | None) -> str:
    if not seconds or seconds < 0:
        return "?:??"
    minutes, secs = divmod(int(seconds), 60)
    return f"{minutes}:{secs:02d}"


def intro_message(ad_contact: str) -> str:
    contact = escape(ad_contact)
    return (
        "🎧 <b>Песни и альбомы из SoundCloud</b>\n"
        "⌨️ Поиск по названию или ссылке\n\n"
        f"💬 Реклама - <code>{contact}</code>"
    )


def render_tracks(
    query: str,
    tracks: list[Track],
    page: int,
    per_page: int,
    link_builder: Callable[[Track], str] | None = None,
) -> str:
    start = page * per_page
    visible = tracks[start : start + per_page]
    if not visible:
        return f"Ничего не нашёл по запросу <b>{escape(query)}</b>."

    lines = []
    for index, track in enumerate(visible):
        marker = relevance_marker(start + index)
        title = escape(track.title)
        artist = escape(track.display_artist)
        link = link_builder(track) if link_builder else track.url
        url = escape(link, quote=True)
        duration = format_duration(track.duration)
        prefix = f"{marker} · " if marker else ""
        lines.append(f"{prefix}{duration} · <a href=\"{url}\">{title}</a> · {artist}")
    return "\n".join(lines)


def render_section_items(
    query: str,
    section: str,
    tracks: list[Track],
    page: int,
    per_page: int,
) -> str:
    start = page * per_page
    visible = tracks[start : start + per_page]
    if not visible:
        label = {"albums": "альбомов", "playlists": "плейлистов", "songs": "песен"}.get(section, "результатов")
        return f"Не нашёл {label} по запросу <b>{escape(query)}</b>."

    lines = []
    for track in visible:
        title = escape(track.title)
        artist = escape(track.display_artist)
        url = escape(track.url, quote=True)
        lines.append(f"· <a href=\"{url}\">{title}</a> · {artist}")
    return "\n".join(lines)


def relevance_marker(result_index: int) -> str:
    if result_index == 0:
        return "‼️"
    if result_index == 1:
        return "❗"
    return ""


def tab_placeholder(tab: str, query: str) -> str:
    label = {"albums": "Альбомы", "playlists": "Плейлисты"}.get(tab, "Раздел")
    return (
        f"<b>{label}</b>\n"
        f"Раздел выбран для запроса <b>{escape(query)}</b>."
    )
