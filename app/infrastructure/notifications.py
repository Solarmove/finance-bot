from html import escape

import structlog

from app.application.dto import TransactionDTO
from app.application.notifications import TransactionNotifier
from app.infrastructure.telegram import RichMessageSender

logger = structlog.get_logger()


class TelegramTransactionNotifier(TransactionNotifier):
    def __init__(self, sender: RichMessageSender) -> None:
        self._sender = sender

    async def expense_created(self, telegram_user_id: int, transaction: TransactionDTO) -> None:
        try:
            await self._sender.send(
                telegram_user_id,
                "<h2>🔗 Расход через API</h2>"
                "<table bordered>"
                f'<tr><th>Сумма</th><td align="right"><b>−{transaction.amount:.2f} '
                f"{transaction.currency}</b></td></tr>"
                f"<tr><th>Категория</th><td>{escape(transaction.category)}</td></tr>"
                "</table>",
            )
        except Exception:
            logger.warning(
                "expense_notification_failed",
                transaction_id=str(transaction.id),
                exc_info=True,
            )
