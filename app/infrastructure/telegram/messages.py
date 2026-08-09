import structlog
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import InputRichMessage, Message

logger = structlog.get_logger()

MARKDOWN_TOKENS = ("**", "__", "~~", "==", "||", "`")


def rich_markdown_to_plain_text(markdown: str) -> str:
    lines: list[str] = []
    for raw_line in markdown.splitlines():
        line = raw_line.strip()
        if not line or line == "---":
            continue
        if line.startswith("#"):
            line = line.lstrip("#").lstrip()
        if _is_table_separator(line):
            continue
        if line.startswith("|") and line.endswith("|"):
            line = "  ".join(cell.strip() for cell in line.strip("|").split("|"))
        for token in MARKDOWN_TOKENS:
            line = line.replace(token, "")
        line = line.replace(r"\|", "|").replace("\\", "")
        if line:
            lines.append(line)
    return "\n".join(lines)[:4096]


def _is_table_separator(line: str) -> bool:
    if "|" not in line or "-" not in line:
        return False
    return not line.translate(str.maketrans("", "", "|:- "))


async def answer_rich_or_plain(message: Message, markdown: str) -> Message:
    try:
        return await message.answer_rich(
            rich_message=InputRichMessage(markdown=markdown),
        )
    except TelegramBadRequest as error:
        logger.warning(
            "rich_message_unavailable",
            chat_id=message.chat.id,
            telegram_error=str(error),
        )
        return await message.answer(
            text=rich_markdown_to_plain_text(markdown),
            parse_mode=None,
        )


async def send_rich_or_plain(bot: Bot, chat_id: int, markdown: str) -> Message:
    try:
        return await bot.send_rich_message(
            chat_id=chat_id,
            rich_message=InputRichMessage(markdown=markdown),
        )
    except TelegramBadRequest as error:
        logger.warning(
            "rich_message_unavailable",
            chat_id=chat_id,
            telegram_error=str(error),
        )
        return await bot.send_message(
            chat_id=chat_id,
            text=rich_markdown_to_plain_text(markdown),
            parse_mode=None,
        )
