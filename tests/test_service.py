from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import create_async_engine

from app.application.dto import CreateTransactionCommand, RecordTelegramTransactionCommand
from app.application.services import FinanceService
from app.application.uow import SqlAlchemyUnitOfWork
from app.application.use_cases import RecordTelegramTransaction
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


async def test_record_telegram_transaction_use_case_owns_transport_mapping(
    service: FinanceService,
) -> None:
    occurred_at = datetime(2026, 8, 9, 10, 30, tzinfo=UTC)
    use_case = RecordTelegramTransaction(service, clock=lambda: occurred_at)

    result = await use_case.execute(
        RecordTelegramTransactionCommand(
            telegram_user_id=1003,
            username="bob",
            first_name="Bob",
            kind=TransactionKind.INCOME,
            amount=Decimal("500.00"),
            currency="PLN",
            category="salary",
            note="August",
        )
    )

    assert result.transaction.occurred_at == occurred_at
    assert result.transaction.source is TransactionSource.TELEGRAM
    assert result.transaction.kind is TransactionKind.INCOME
