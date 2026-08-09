from dataclasses import dataclass
from decimal import Decimal

from app.domain.enums import TransactionKind


@dataclass(frozen=True, slots=True)
class ParsedTransaction:
    kind: TransactionKind
    amount: Decimal
    category: str
    note: str | None
