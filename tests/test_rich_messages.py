from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4
from zoneinfo import ZoneInfo

from app.application.dto import TransactionDTO
from app.bot.views import transaction_history
from app.domain.enums import TransactionKind, TransactionSource
from app.infrastructure.telegram.rich_messages import (
    InputRichMessage,
    RichMessageSender,
    SendRichMessage,
)


def test_history_uses_native_rich_message_table() -> None:
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

    html = transaction_history([transaction], ZoneInfo("Europe/Warsaw"))

    assert "<table bordered striped>" in html
    assert "<th>Дата</th>" in html
    assert "Еда &lt;кофе&gt;" in html
    assert "<pre>" not in html


def test_send_rich_message_serializes_bot_api_10_2_payload() -> None:
    method = SendRichMessage(
        chat_id=42,
        rich_message=InputRichMessage(html="<h1>Баланс</h1>"),
    )

    payload = method.model_dump(exclude_none=True)

    assert method.__api_method__ == "sendRichMessage"
    assert payload["chat_id"] == 42
    assert payload["rich_message"]["html"] == "<h1>Баланс</h1>"


def test_rich_message_plain_text_fallback_removes_rich_tags() -> None:
    html = "<h1>История</h1><table><tr><th>Дата</th><th>Сумма</th></tr></table>"

    text = RichMessageSender.to_plain_text(html)

    assert "История" in text
    assert "Дата" in text
    assert "Сумма" in text
    assert "<table>" not in text
