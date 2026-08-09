from aiogram.types import Message

from app.application.dto import RecordTelegramTransactionCommand
from app.application.use_cases import RecordTelegramTransaction
from app.bot.controllers.base import BotController
from app.bot.parsing import CommandParseError, parse_transaction_command
from app.bot.views import transaction_created, transaction_parse_error
from app.domain.enums import TransactionKind


class TransactionController(BotController):
    def __init__(
        self,
        use_case: RecordTelegramTransaction,
        currency: str,
    ) -> None:
        self._use_case = use_case
        self._currency = currency

    async def record(self, message: Message, kind: TransactionKind) -> None:
        if message.from_user is None or message.text is None:
            return
        try:
            parsed = parse_transaction_command(message.text, kind)
        except CommandParseError as error:
            command = "expense" if kind is TransactionKind.EXPENSE else "income"
            await self.answer(message, transaction_parse_error(str(error), command))
            return

        result = await self._use_case.execute(
            RecordTelegramTransactionCommand(
                telegram_user_id=message.from_user.id,
                username=message.from_user.username,
                first_name=message.from_user.first_name,
                kind=kind,
                amount=parsed.amount,
                currency=self._currency,
                category=parsed.category,
                note=parsed.note,
            )
        )
        await self.answer(message, transaction_created(result.transaction))
