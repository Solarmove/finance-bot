from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class Balance:
    income: Decimal
    expense: Decimal

    @property
    def net(self) -> Decimal:
        return self.income - self.expense
