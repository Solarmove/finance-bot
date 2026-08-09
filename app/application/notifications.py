from typing import Protocol

from app.application.dto import TransactionDTO


class TransactionNotifier(Protocol):
    async def expense_created(self, telegram_user_id: int, transaction: TransactionDTO) -> None: ...
