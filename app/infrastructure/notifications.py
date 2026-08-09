import structlog
from aiogram import Bot

from app.application.dto import TransactionDTO
from app.application.notifications import TransactionNotifier
from app.infrastructure.telegram import send_rich_or_plain
from app.infrastructure.telegram.markdown import escape_table_cell

logger = structlog.get_logger()


class TelegramTransactionNotifier(TransactionNotifier):
    def __init__(self, bot: Bot) -> None:
        self._bot = bot

    async def expense_created(self, telegram_user_id: int, transaction: TransactionDTO) -> None:
        try:
            markdown = (
                "## 🔗 Расход через API\n\n"
                "| | |\n"
                "|:--|--:|\n"
                f"| **Сумма** | **−{transaction.amount:.2f} {transaction.currency}** |\n"
                f"| **Категория** | {escape_table_cell(transaction.category)} |"
            )
            await send_rich_or_plain(self._bot, telegram_user_id, markdown)
        except Exception:
            logger.warning(
                "expense_notification_failed",
                transaction_id=str(transaction.id),
                exc_info=True,
            )
