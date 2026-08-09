from decimal import Decimal

import pytest

from app.bot.parsing import CommandParseError, parse_transaction_command
from app.domain.enums import TransactionKind


def test_parse_expense_with_comma_and_note() -> None:
    parsed = parse_transaction_command(
        "/expense 125,50 продукты деловой обед", TransactionKind.EXPENSE
    )

    assert parsed.amount == Decimal("125.50")
    assert parsed.category == "продукты"
    assert parsed.note == "деловой обед"


@pytest.mark.parametrize("amount", ["0", "-1", "NaN", "12.345", "not-a-number"])
def test_reject_invalid_amount(amount: str) -> None:
    with pytest.raises(CommandParseError):
        parse_transaction_command(f"/expense {amount} продукты", TransactionKind.EXPENSE)
