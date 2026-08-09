from collections.abc import Callable
from datetime import UTC, datetime

from app.application.dto import (
    CreateTransactionCommand,
    CreateTransactionResult,
    RecordTelegramTransactionCommand,
)
from app.application.services import FinanceService
from app.domain.enums import TransactionSource


def utc_now() -> datetime:
    return datetime.now(UTC)


class RecordTelegramTransaction:
    def __init__(
        self,
        finance_service: FinanceService,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        self._finance_service = finance_service
        self._clock = clock

    async def execute(self, command: RecordTelegramTransactionCommand) -> CreateTransactionResult:
        return await self._finance_service.create_transaction(
            CreateTransactionCommand(
                telegram_user_id=command.telegram_user_id,
                username=command.username,
                first_name=command.first_name,
                kind=command.kind,
                amount=command.amount,
                currency=command.currency,
                category=command.category,
                note=command.note,
                occurred_at=self._clock(),
                source=TransactionSource.TELEGRAM,
            )
        )
