from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock
from uuid import uuid4
from zoneinfo import ZoneInfo

from aiogram.exceptions import TelegramBadRequest
from aiogram.methods import SendRichMessage
from aiogram.types import InputRichMessage, Message

from app.application.dto import TransactionDTO
from app.bot.views import transaction_history
from app.domain.enums import TransactionKind, TransactionSource
from app.infrastructure.telegram import answer_rich_or_plain, rich_markdown_to_plain_text


def test_history_uses_native_rich_markdown_table() -> None:
    transaction = TransactionDTO(
        id=uuid4(),
        kind=TransactionKind.EXPENSE,
        amount=Decimal("19.90"),
        currency="PLN",
        category="Еда <кофе>",
        note=None,
        occurred_at=datetime(2026, 8, 9, 12, 0, tzinfo=UTC),
        source=TransactionSource.TELEGRAM,
        external_id=None,
    )

    markdown = transaction_history([transaction], ZoneInfo("Europe/Warsaw"))

    assert "| Дата | Тип | Категория | Сумма |" in markdown
    assert "|:--|:--|:--|--:|" in markdown
    assert r"Еда \<кофе\>" in markdown
    assert "<table" not in markdown


def test_native_aiogram_send_rich_message_serializes_payload() -> None:
    method = SendRichMessage(
        chat_id=42,
        rich_message=InputRichMessage(markdown="# Баланс"),
    )

    payload = method.model_dump(exclude_none=True)

    assert method.__api_method__ == "sendRichMessage"
    assert payload["chat_id"] == 42
    assert payload["rich_message"]["markdown"] == "# Баланс"


def test_plain_text_fallback_keeps_rich_message_readable() -> None:
    markdown = "# История\n\n| Дата | Сумма |\n|:--|--:|\n| 09.08 | **10 PLN** |"

    text = rich_markdown_to_plain_text(markdown)

    assert text == "История\nДата  Сумма\n09.08  10 PLN"


async def test_answer_rich_falls_back_to_regular_answer() -> None:
    rich_method = SendRichMessage(
        chat_id=42,
        rich_message=InputRichMessage(markdown="# Баланс"),
    )
    plain_message = cast(Message, object())
    telegram_message = SimpleNamespace(
        chat=SimpleNamespace(id=42),
        answer_rich=AsyncMock(
            side_effect=TelegramBadRequest(
                method=rich_method,
                message="rich messages are unavailable",
            )
        ),
        answer=AsyncMock(return_value=plain_message),
    )

    result = await answer_rich_or_plain(
        cast(Message, telegram_message),
        "# Баланс\n\n**100 PLN**",
    )

    assert result is plain_message
    telegram_message.answer.assert_awaited_once_with(
        text="Баланс\n100 PLN",
        parse_mode=None,
    )
