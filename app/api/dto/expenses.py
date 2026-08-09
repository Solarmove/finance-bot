from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

Currency = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=3)]


class ExpenseCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    currency: Currency = "PLN"
    category: str = Field(min_length=1, max_length=64)
    note: str | None = Field(default=None, max_length=500)
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    notify: bool = False

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        if not value.isalpha():
            raise ValueError("currency must contain only letters")
        return value.upper()

    @field_validator("occurred_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("occurred_at must include a timezone offset")
        return value


class ExpenseResponse(BaseModel):
    id: UUID
    status: str
    amount: Decimal
    currency: str
    category: str
    occurred_at: datetime
