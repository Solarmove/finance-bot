from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import create_async_engine

from app.application.dto import CreateTransactionCommand
from app.application.services import FinanceService
from app.application.uow import SqlAlchemyUnitOfWork
from app.domain.enums import TransactionKind, TransactionSource
from app.infrastructure.database import create_session_factory
from app.infrastructure.models import Base


@pytest.fixture
async def service() -> FinanceService:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = create_session_factory(engine)
    instance = FinanceService(
        uow_factory=lambda: SqlAlchemyUnitOfWork(session_factory),
        default_timezone="Europe/Warsaw",
    )
    yield instance
    await engine.dispose()


async def test_api_key_is_hashed_and_can_be_rotated(service: FinanceService) -> None:
    registration = await service.ensure_user(1001, "alice", "Alice")

    assert registration.api_key is not None
    assert registration.api_key.startswith("fb_")
    assert not hasattr(registration.user, "api_key_hash")
    assert await service.authenticate_api_key(registration.api_key) is not None

    replacement = await service.rotate_api_key(1001)

    assert await service.authenticate_api_key(registration.api_key) is None
    assert await service.authenticate_api_key(replacement) is not None


async def test_idempotent_transaction_and_balance(service: FinanceService) -> None:
    registration = await service.ensure_user(1002)
    assert registration.api_key is not None
    now = datetime.now(UTC)
    command = CreateTransactionCommand(
        telegram_user_id=1002,
        kind=TransactionKind.EXPENSE,
        amount=Decimal("42.10"),
        currency="PLN",
        category="food",
        note=None,
        occurred_at=now,
        source=TransactionSource.API,
        external_id="api:test-idempotency-key",
    )

    first = await service.create_transaction(command)
    second = await service.create_transaction(command)
    balance = await service.balance(1002, now - timedelta(days=1), now + timedelta(days=1))

    assert first.created is True
    assert second.created is False
    assert first.transaction.id == second.transaction.id
    assert balance.expense == Decimal("42.10")
    assert balance.net == Decimal("-42.10")
