from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from models import Track


def results_keyboard(
    search_key: str,
    tracks: list[Track],
    page: int,
    per_page: int,
) -> InlineKeyboardMarkup:
    start = page * per_page
    rows: list[list[InlineKeyboardButton]] = []

    nav_row: list[InlineKeyboardButton] = []
    if page > 0:
        nav_row.append(
            InlineKeyboardButton(
                text="«",
                callback_data=f"page:{search_key}:{page - 1}",
            )
        )
    if start + per_page < len(tracks):
        nav_row.append(
            InlineKeyboardButton(
                text="»",
                callback_data=f"page:{search_key}:{page + 1}",
            )
        )
    if nav_row:
        rows.append(nav_row)

    rows.append(
        [
            InlineKeyboardButton(text="Песни", callback_data=f"menu:{search_key}:{page}:songs"),
            InlineKeyboardButton(text="Скачать", callback_data=f"download_page:{search_key}:{page}"),
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def category_keyboard(selected: str | None, search_key: str, page: int) -> InlineKeyboardMarkup:
    labels = {
        "songs": "Песни",
        "albums": "Альбомы",
        "playlists": "Плейлисты",
    }

    def button(section: str) -> InlineKeyboardButton:
        label = labels[section]
        if section == selected:
            label = f"📍 {label}"
        return InlineKeyboardButton(text=label, callback_data=f"section:{section}:{search_key}:0")

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [button("songs"), button("albums")],
            [button("playlists")],
        ]
    )


def section_keyboard(
    section: str,
    search_key: str,
    page: int,
    total: int,
    per_page: int,
) -> InlineKeyboardMarkup:
    labels = {
        "songs": "Песни",
        "albums": "Альбомы",
        "playlists": "Плейлисты",
    }
    rows: list[list[InlineKeyboardButton]] = []

    nav_row: list[InlineKeyboardButton] = []
    if page > 0:
        nav_row.append(
            InlineKeyboardButton(
                text="«",
                callback_data=f"section:{section}:{search_key}:{page - 1}",
            )
        )
    if (page + 1) * per_page < total:
        nav_row.append(
            InlineKeyboardButton(
                text="»",
                callback_data=f"section:{section}:{search_key}:{page + 1}",
            )
        )
    if nav_row:
        rows.append(nav_row)

    label = labels.get(section, "Раздел")
    rows.append([InlineKeyboardButton(text=label, callback_data=f"menu:{search_key}:0:{section}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def source_keyboard(track: Track) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Открыть трек", url=track.url)]]
    )
    
