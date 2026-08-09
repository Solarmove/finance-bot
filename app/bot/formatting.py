from datetime import tzinfo
from decimal import Decimal
from html import escape

from app.application.dto import TransactionDTO


def money(value: Decimal, currency: str) -> str:
    return f"{value:,.2f} {currency}".replace(",", " ")


def _truncate(value: str, width: int) -> str:
    return value if len(value) <= width else f"{value[: width - 1]}…"


def transaction_table(transactions: list[TransactionDTO], timezone: tzinfo) -> str:
    headers = ("Дата", "Категория", "Сумма")
    rows: list[tuple[str, str, str]] = []
    for transaction in transactions:
        sign = "−" if transaction.kind.value == "expense" else "+"
        rows.append(
            (
                transaction.occurred_at.astimezone(timezone).strftime("%d.%m"),
                _truncate(transaction.category, 14),
                f"{sign}{transaction.amount:.2f} {transaction.currency}",
            )
        )

    widths = [len(header) for header in headers]
    for row in rows:
        for index, cell in enumerate(row):
            widths[index] = max(widths[index], len(cell))

    def render(row: tuple[str, str, str]) -> str:
        return f"{row[0]:<{widths[0]}}  {row[1]:<{widths[1]}}  {row[2]:>{widths[2]}}"

    separator = "  ".join("─" * width for width in widths)
    table = "\n".join([render(headers), separator, *(render(row) for row in rows)])
    return f"<pre>{escape(table)}</pre>"
