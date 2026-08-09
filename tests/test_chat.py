import pytest
from aiogram.enums import ChatType

from app.bot.chat import is_private_chat


@pytest.mark.parametrize("chat_type", [ChatType.PRIVATE, ChatType.PRIVATE.value, "private"])
def test_private_chat_is_detected_for_enum_and_raw_value(chat_type: ChatType | str) -> None:
    assert is_private_chat(chat_type) is True


@pytest.mark.parametrize("chat_type", [ChatType.GROUP, ChatType.SUPERGROUP, "channel"])
def test_non_private_chat_is_rejected(chat_type: ChatType | str) -> None:
    assert is_private_chat(chat_type) is False
