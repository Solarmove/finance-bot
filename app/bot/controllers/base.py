from aiogram.types import Message

from app.infrastructure.telegram import answer_rich_or_plain


class BotController:
    async def answer(self, message: Message, markdown: str) -> None:
        await answer_rich_or_plain(message, markdown)
