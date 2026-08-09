from decimal import Decimal, InvalidOperation

from app.bot.dto import ParsedTransaction
from app.domain.enums import TransactionKind


class CommandParseError(ValueError):
    pass


def parse_transaction_command(text: str, kind: TransactionKind) -> ParsedTransaction:
    parts = text.strip().split(maxsplit=3)
    if len(parts) < 3:
        raise CommandParseError("Укажите сумму и категорию")

    try:
        amount = Decimal(parts[1].replace(",", "."))
    except InvalidOperation as error:
        raise CommandParseError("Сумма должна быть числом") from error

    if not amount.is_finite() or amount <= 0:
        raise CommandParseError("Сумма должна быть больше нуля")
    exponent = amount.as_tuple().exponent
    if isinstance(exponent, int) and exponent < -2:
        raise CommandParseError("Используйте не более двух знаков после запятой")
    if amount >= Decimal("10000000000000000"):
        raise CommandParseError("Сумма слишком велика")

    category = parts[2].strip()
    note = parts[3].strip() if len(parts) == 4 else None
    if len(category) > 64:
        raise CommandParseError("Категория не должна превышать 64 символа")
    if note and len(note) > 500:
        raise CommandParseError("Комментарий не должен превышать 500 символов")

    return ParsedTransaction(kind=kind, amount=amount, category=category, note=note)
