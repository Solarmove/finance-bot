from html import escape

import structlog
from aiogram import Bot

from app.application.dto import TransactionDTO
from app.application.notifications import TransactionNotifier

logger = structlog.get_logger()


class TelegramTransactionNotifier(TransactionNotifier):
    def __init__(self, bot: Bot) -> None:
        self._bot = bot

    async def expense_created(self, telegram_user_id: int, transaction: TransactionDTO) -> None:
        try:
            await self._bot.send_message(
                telegram_user_id,
                (
                    "<b>Расход добавлен через API</b>\n"
                    f"−{transaction.amount:.2f} {transaction.currency} · "
                    f"{escape(transaction.category)}"
                ),
            )
        except Exception:
            logger.warning(
                "expense_notification_failed",
                transaction_id=str(transaction.id),
                exc_info=True,
            )
