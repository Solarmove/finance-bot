from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.api.dto import ExpenseCreate


def test_expense_dto_normalizes_currency() -> None:
    payload = ExpenseCreate.model_validate(
        {"amount": "12.30", "currency": "pln", "category": "food"}
    )

    assert payload.amount == Decimal("12.30")
    assert payload.currency == "PLN"
    assert payload.occurred_at.tzinfo is not None


def test_expense_dto_does_not_accept_user_id() -> None:
    with pytest.raises(ValidationError):
        ExpenseCreate.model_validate(
            {"telegram_user_id": 42, "amount": "12.30", "category": "food"}
        )
