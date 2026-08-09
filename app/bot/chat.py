from aiogram.enums import ChatType


def is_private_chat(chat_type: ChatType | str) -> bool:
    value = chat_type.value if isinstance(chat_type, ChatType) else chat_type
    return value == ChatType.PRIVATE.value
