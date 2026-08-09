from abc import ABC, abstractmethod
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from app.domain.enums import TransactionKind
from app.infrastructure.models import Transaction, User


class UserRepository(ABC):
    @abstractmethod
    async def get_by_telegram_id(self, telegram_user_id: int) -> User | None: ...

    @abstractmethod
    async def get_by_api_key_prefix(self, prefix: str) -> User | None: ...

    @abstractmethod
    def add(self, user: User) -> None: ...


class TransactionRepository(ABC):
    @abstractmethod
    def add(self, transaction: Transaction) -> None: ...

    @abstractmethod
    async def get_by_external_id(self, external_id: str) -> Transaction | None: ...

    @abstractmethod
    async def list_recent(self, user_id: UUID, limit: int = 10) -> list[Transaction]: ...

    @abstractmethod
    async def totals(
        self, user_id: UUID, start: datetime, end: datetime
    ) -> dict[TransactionKind, Decimal]: ...
