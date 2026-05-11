from __future__ import annotations

from aiogram import Bot
from aiogram.types import FSInputFile

from .config import Settings


class StartSticker:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._file_id: str | None = None

    async def send(self, bot: Bot, chat_id: int) -> None:
        file_id = await self._resolve_file_id(bot)
        if file_id:
            await bot.send_sticker(chat_id=chat_id, sticker=file_id)
            return

        if self.settings.fallback_sticker_path.exists():
            media = FSInputFile(self.settings.fallback_sticker_path)
            try:
                await bot.send_sticker(chat_id=chat_id, sticker=media)
            except Exception:
                await bot.send_document(chat_id=chat_id, document=media)

    async def _resolve_file_id(self, bot: Bot) -> str | None:
        if self._file_id:
            return self._file_id

        try:
            sticker_set = await bot.get_sticker_set(self.settings.sticker_set_name)
        except Exception:
            return None

        index = self.settings.sticker_index - 1
        if index < 0 or index >= len(sticker_set.stickers):
            return None

        self._file_id = sticker_set.stickers[index].file_id
        return self._file_id
