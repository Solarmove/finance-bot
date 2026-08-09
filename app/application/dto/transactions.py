from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from app.domain.enums import TransactionKind, TransactionSource


@dataclass(frozen=True, slots=True)
class TransactionDTO:
    id: UUID
    kind: TransactionKind
    amount: Decimal
    currency: str
    category: str
    note: str | None
    occurred_at: datetime
    source: TransactionSource
    external_id: str | None


@dataclass(frozen=True, slots=True)
class CreateTransactionCommand:
    telegram_user_id: int
    kind: TransactionKind
    amount: Decimal
    currency: str
    category: str
    note: str | None
    occurred_at: datetime
    source: TransactionSource
    external_id: str | None = None
    username: str | None = None
    first_name: str | None = None


@dataclass(frozen=True, slots=True)
class CreateTransactionResult:
    transaction: TransactionDTO
    created: bool
