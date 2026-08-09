from datetime import datetime
from decimal import Decimal
from typing import cast
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.repositories import TransactionRepository, UserRepository
from app.domain.enums import TransactionKind
from app.infrastructure.models import Transaction, User


class SqlAlchemyUserRepository(UserRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_telegram_id(self, telegram_user_id: int) -> User | None:
        statement = select(User).where(User.telegram_user_id == telegram_user_id)
        return cast(User | None, await self._session.scalar(statement))

    async def get_by_api_key_prefix(self, prefix: str) -> User | None:
        statement = select(User).where(User.api_key_prefix == prefix)
        return cast(User | None, await self._session.scalar(statement))

    def add(self, user: User) -> None:
        self._session.add(user)


class SqlAlchemyTransactionRepository(TransactionRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(self, transaction: Transaction) -> None:
        self._session.add(transaction)

    async def get_by_external_id(self, external_id: str) -> Transaction | None:
        statement = select(Transaction).where(Transaction.external_id == external_id)
        return cast(Transaction | None, await self._session.scalar(statement))

    async def list_recent(self, user_id: UUID, limit: int = 10) -> list[Transaction]:
        statement = (
            select(Transaction)
            .where(Transaction.user_id == user_id)
            .order_by(Transaction.occurred_at.desc())
            .limit(limit)
        )
        result = await self._session.scalars(statement)
        return list(result)

    async def totals(
        self, user_id: UUID, start: datetime, end: datetime
    ) -> dict[TransactionKind, Decimal]:
        statement = (
            select(Transaction.kind, func.coalesce(func.sum(Transaction.amount), 0))
            .where(
                Transaction.user_id == user_id,
                Transaction.occurred_at >= start,
                Transaction.occurred_at < end,
            )
            .group_by(Transaction.kind)
        )
        rows = (await self._session.execute(statement)).all()
        totals = {kind: Decimal("0") for kind in TransactionKind}
        totals.update({kind: Decimal(amount) for kind, amount in rows})
        return totals
