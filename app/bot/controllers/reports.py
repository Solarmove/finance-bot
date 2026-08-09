from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from aiogram.types import Message

from app.application.services import FinanceService
from app.bot.controllers.base import BotController
from app.bot.views import empty_history, monthly_balance, transaction_history


class ReportController(BotController):
    def __init__(
        self,
        finance_service: FinanceService,
        currency: str,
        timezone: str,
    ) -> None:
        self._finance_service = finance_service
        self._currency = currency
        self._timezone = ZoneInfo(timezone)

    async def balance(self, message: Message) -> None:
        if message.from_user is None:
            return
        now = datetime.now(self._timezone)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        summary = await self._finance_service.balance(
            message.from_user.id,
            month_start.astimezone(UTC),
            now.astimezone(UTC),
        )
        await self.answer(message, monthly_balance(summary, self._currency, now))

    async def history(self, message: Message) -> None:
        if message.from_user is None:
            return
        transactions = await self._finance_service.recent_transactions(
            message.from_user.id, limit=10
        )
        view = (
            transaction_history(transactions, self._timezone) if transactions else empty_history()
        )
        await self.answer(message, view)
