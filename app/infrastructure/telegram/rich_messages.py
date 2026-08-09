import re
from html import unescape
from typing import ClassVar

import structlog
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.methods.base import TelegramMethod
from aiogram.types import Message
from aiogram.types.base import TelegramObject

logger = structlog.get_logger()

BLOCK_END_PATTERN = re.compile(
    r"</(?:h[1-6]|p|footer|blockquote|aside|li|tr|details|table)>", re.IGNORECASE
)
CELL_END_PATTERN = re.compile(r"</t[dh]>", re.IGNORECASE)
TAG_PATTERN = re.compile(r"<[^>]+>")


class InputRichMessage(TelegramObject):
    """Bot API 10.2 InputRichMessage subset used by the application."""

    html: str
    skip_entity_detection: bool | None = None


class SendRichMessage(TelegramMethod[Message]):
    """Temporary aiogram adapter for Bot API 10.2 sendRichMessage."""

    __returning__: ClassVar[type[Message]] = Message
    __api_method__: ClassVar[str] = "sendRichMessage"

    chat_id: int | str
    rich_message: InputRichMessage
    message_thread_id: int | None = None
    disable_notification: bool | None = None
    protect_content: bool | None = None


class RichMessageSender:
    def __init__(self, bot: Bot) -> None:
        self._bot = bot

    async def send(
        self,
        chat_id: int | str,
        html: str,
        *,
        message_thread_id: int | None = None,
    ) -> Message:
        try:
            return await self._bot(
                SendRichMessage(
                    chat_id=chat_id,
                    rich_message=InputRichMessage(html=html),
                    message_thread_id=message_thread_id,
                )
            )
        except TelegramBadRequest as error:
            logger.warning(
                "rich_message_fallback",
                chat_id=chat_id,
                telegram_error=str(error),
            )
            return await self._bot.send_message(
                chat_id=chat_id,
                text=self.to_plain_text(html),
                message_thread_id=message_thread_id,
                parse_mode=None,
            )

    @staticmethod
    def to_plain_text(html: str) -> str:
        text = CELL_END_PATTERN.sub("  ", html)
        text = BLOCK_END_PATTERN.sub("\n", text)
        text = TAG_PATTERN.sub("", text)
        lines = [line.strip() for line in unescape(text).splitlines()]
        normalized = "\n".join(line for line in lines if line)
        return normalized[:4096]
