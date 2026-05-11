from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from html import escape

from aiogram import Bot, Dispatcher, F, Router
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, FSInputFile, InputMediaAudio, Message
from aiogram.client.default import DefaultBotProperties

from cache import ResultCache
from config import Settings, load_settings
from formatting import intro_message, render_section_items, render_tracks
from keyboards import category_keyboard, results_keyboard, section_keyboard, source_keyboard
from models import Track
from soundcloud import SoundCloudClient
from stickers import StartSticker

router = Router()
cache = ResultCache()
settings: Settings
soundcloud: SoundCloudClient
start_sticker: StartSticker
bot_username: str | None = None


@router.message(CommandStart())
async def handle_start(message: Message) -> None:
    if not message.chat:
        return
    payload = _start_payload(message)
    if payload.startswith("track-"):
        await _handle_single_track_deeplink(message, payload.removeprefix("track-"))
        return
    await start_sticker.send(message.bot, message.chat.id)
    await message.answer(intro_message(settings.ad_contact))


@router.message(F.text)
async def handle_query(message: Message) -> None:
    query = (message.text or "").strip()
    if len(query) < 3 or query.startswith("/"):
        return
    try:
        tracks = await soundcloud.search(query)
    except Exception as exc:
        logging.exception("SoundCloud search failed")
        await message.answer(f"Не получилось найти треки: <code>{exc}</code>")
        return
    search_key = cache.put_search(query, tracks)
    await message.answer(
        render_tracks(
            query,
            tracks,
            page=0,
            per_page=settings.results_per_page,
            link_builder=_deep_link,
        ),
        reply_markup=results_keyboard(
            search_key,
            tracks,
            page=0,
            per_page=settings.results_per_page,
        ),
        disable_web_page_preview=True,
    )


@router.callback_query(F.data == "noop")
async def handle_noop(callback: CallbackQuery) -> None:
    await callback.answer()


@router.callback_query(F.data.startswith("page:"))
async def handle_page(callback: CallbackQuery) -> None:
    if not callback.message or not callback.data:
        await callback.answer()
        return
    _, search_key, raw_page = callback.data.split(":", 2)
    search = cache.get_search(search_key)
    if not search:
        await callback.answer("Результаты устарели. Отправьте запрос ещё раз.", show_alert=True)
        return
    page = _safe_page(raw_page)
    await callback.message.edit_text(
        render_tracks(
            search.query,
            search.tracks,
            page=page,
            per_page=settings.results_per_page,
            link_builder=_deep_link,
        ),
        reply_markup=results_keyboard(
            search_key,
            search.tracks,
            page=page,
            per_page=settings.results_per_page,
        ),
        disable_web_page_preview=True,
    )
    await callback.answer()


@router.callback_query(F.data.startswith("menu:"))
async def handle_category_menu(callback: CallbackQuery) -> None:
    if not callback.message or not callback.data:
        await callback.answer()
        return
    _, search_key, raw_page, selected = callback.data.split(":", 3)
    search = cache.get_search(search_key)
    if not search:
        await callback.answer("Результаты устарели. Отправьте запрос ещё раз.", show_alert=True)
        return
    page = _safe_page(raw_page)
    await callback.message.edit_reply_markup(
        reply_markup=category_keyboard(selected or None, search_key, page)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("section:"))
async def handle_section(callback: CallbackQuery) -> None:
    if not callback.message or not callback.data:
        await callback.answer()
        return
    _, section, search_key, raw_page = callback.data.split(":", 3)
    search = cache.get_search(search_key)
    if not search:
        await callback.answer("Результаты устарели. Отправьте запрос ещё раз.", show_alert=True)
        return
    await callback.answer("Открываю...")
    page = _safe_page(raw_page)
    try:
        tracks = await _section_tracks(search_key, section)
    except Exception as exc:
        logging.exception("SoundCloud section search failed")
        await callback.message.edit_text(f"Не получилось открыть раздел: <code>{exc}</code>")
        return
    if section == "songs":
        text = render_tracks(
            search.query,
            tracks,
            page=page,
            per_page=settings.results_per_page,
            link_builder=_deep_link,
        )
    else:
        text = render_section_items(
            search.query,
            section,
            tracks,
            page=page,
            per_page=settings.results_per_page,
        )
    await callback.message.edit_text(
        text,
        reply_markup=section_keyboard(
            section,
            search_key,
            page,
            total=len(tracks),
            per_page=settings.results_per_page,
        ),
        disable_web_page_preview=True,
    )


@router.callback_query(F.data.startswith("download_page:"))
async def handle_download_page(callback: CallbackQuery) -> None:
    if not callback.message or not callback.data:
        await callback.answer()
        return
    _, search_key, raw_page = callback.data.split(":", 2)
    search = cache.get_search(search_key)
    if not search:
        await callback.answer("Результаты устарели. Отправьте запрос ещё раз.", show_alert=True)
        return
    page = _safe_page(raw_page)
    start = page * settings.results_per_page
    tracks = search.tracks[start : start + settings.results_per_page]
    if not tracks:
        await callback.answer("На этой странице нет треков.", show_alert=True)
        return
    if not settings.allow_audio_downloads:
        await callback.message.answer(_source_links_message(tracks), disable_web_page_preview=True)
        await callback.answer()
        return
    await callback.answer(f"Загружаю файлов: {len(tracks)}")
    await _download_and_send_group(callback.message, tracks)


async def _handle_single_track_deeplink(message: Message, track_key: str) -> None:
    track = cache.get_track(track_key)
    if not track:
        await message.answer("Этот трек уже устарел в кеше. Повторите поиск.")
        return
    if not settings.allow_audio_downloads:
        await message.answer(
            "Скачивание файлов выключено. Откройте трек по ссылке:",
            reply_markup=source_keyboard(track),
        )
        return
    await _download_and_send(message, track)


async def _download_and_send(message: Message, track: Track) -> None:
    try:
        path = await soundcloud.download(track, settings.downloads_dir)
        if path.stat().st_size > settings.max_audio_bytes:
            path.unlink(missing_ok=True)
            await message.answer(
                f"Файл больше лимита {settings.max_audio_mb} МБ. Откройте трек по ссылке:",
                reply_markup=source_keyboard(track),
            )
            return
        await _send_audio(message, path, track.title, track.artist)
        path.unlink(missing_ok=True)
    except Exception as exc:
        logging.exception("SoundCloud download failed")
        await message.answer(
            f"Не получилось скачать файл: <code>{exc}</code>",
            reply_markup=source_keyboard(track),
        )


async def _download_and_send_group(message: Message, tracks: list[Track]) -> None:
    downloaded: list[tuple[Track, Path]] = []
    failed: list[str] = []
    try:
        for track in tracks:
            try:
                path = await soundcloud.download(track, settings.downloads_dir)
                if path.stat().st_size > settings.max_audio_bytes:
                    path.unlink(missing_ok=True)
                    failed.append(f"{track.display_artist} - {track.title}: больше {settings.max_audio_mb} МБ")
                    continue
                downloaded.append((track, path))
            except Exception as exc:
                logging.exception("SoundCloud grouped download failed")
                failed.append(f"{track.display_artist} - {track.title}: {exc}")
        if downloaded:
            media = [
                InputMediaAudio(
                    media=FSInputFile(path),
                    title=track.title[:64],
                    performer=track.artist[:64],
                    caption=_music_caption(),
                )
                for track, path in downloaded
            ]
            await message.answer_media_group(media=media)
        if failed:
            await message.answer("Не получилось скачать:\n" + "\n".join(f"• {item}" for item in failed[:5]))
    finally:
        for _, path in downloaded:
            path.unlink(missing_ok=True)


async def _section_tracks(search_key: str, section: str) -> list[Track]:
    search = cache.get_search(search_key)
    if not search:
        return []
    if section == "songs":
        return search.tracks
    if section in search.sections:
        return search.sections[section]
    tracks = await soundcloud.search_section(search.query, section)
    cache.put_section(search_key, section, tracks)
    return tracks


async def _send_audio(message: Message, path: Path, title: str, performer: str) -> None:
    media = FSInputFile(path)
    try:
        await message.answer_audio(
            audio=media,
            title=title[:64],
            performer=performer[:64],
            caption=_music_caption(),
        )
    except Exception:
        await message.answer_document(
            document=media,
            caption=f"{performer} - {title}\n{_music_caption()}"[:1024],
        )


def _safe_page(raw_page: str) -> int:
    try:
        return max(0, int(raw_page))
    except ValueError:
        return 0


def _start_payload(message: Message) -> str:
    parts = (message.text or "").split(maxsplit=1)
    return parts[1].strip() if len(parts) > 1 else ""


def _deep_link(track: Track) -> str:
    if not bot_username:
        return track.url
    return f"https://t.me/{bot_username}?start=track-{cache.put_track(track)}"


def _source_links_message(tracks: list[Track]) -> str:
    lines = ["Скачивание файлов выключено. Ссылки на треки страницы:"]
    for track in tracks:
        url = escape(track.url, quote=True)
        title = escape(track.title)
        artist = escape(track.display_artist)
        lines.append(f'• <a href="{url}">{title}</a> · {artist}')
    return "\n".join(lines)


def _music_caption() -> str:
    if bot_username:
        return f'☁️ <a href="https://t.me/{bot_username}">music</a>'
    return "☁️ music"


async def main() -> None:
    global settings, soundcloud, start_sticker, bot_username

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    settings = load_settings()
    soundcloud = SoundCloudClient(search_limit=settings.search_limit)
    start_sticker = StartSticker(settings)

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dispatcher = Dispatcher()
    dispatcher.include_router(router)

    me = await bot.get_me()
    bot_username = me.username

    await dispatcher.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
        
