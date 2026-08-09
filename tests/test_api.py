import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine

from app.api.handlers import router
from app.application.services import FinanceService
from app.application.uow import SqlAlchemyUnitOfWork
from app.core.config import Settings
from app.infrastructure.database import create_session_factory
from app.infrastructure.models import Base


class FakeNotifier:
    async def expense_created(self, *_: object, **__: object) -> None:
        return None


@pytest.fixture
async def api_client() -> tuple[AsyncClient, FinanceService]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = create_session_factory(engine)
    service = FinanceService(
        uow_factory=lambda: SqlAlchemyUnitOfWork(session_factory),
        default_timezone="Europe/Warsaw",
    )
    settings = Settings(
        _env_file=None,
        bot_token="123456789:abcdefghijklmnopqrstuvwxyzABCDE12345",
        webhook_base_url="https://example.com",
        webhook_secret="test_webhook_secret",
    )
    app = FastAPI()
    app.state.settings = settings
    app.state.finance_service = service
    app.state.transaction_notifier = FakeNotifier()
    app.include_router(router)
    client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")

    yield client, service

    await client.aclose()
    await engine.dispose()


async def test_create_expense_is_authenticated_and_idempotent(
    api_client: tuple[AsyncClient, FinanceService],
) -> None:
    client, service = api_client
    registration = await service.ensure_user(9001)
    assert registration.api_key is not None
    headers = {
        "X-API-Key": registration.api_key,
        "Idempotency-Key": "bank-event-0001",
    }
    payload = {"amount": "19.99", "category": "food"}

    first = await client.post("/api/v1/expenses", json=payload, headers=headers)
    second = await client.post("/api/v1/expenses", json=payload, headers=headers)

    assert first.status_code == 201
    assert first.json()["status"] == "created"
    assert second.status_code == 200
    assert second.json()["status"] == "already_exists"


async def test_api_key_identifies_owner_and_keys_are_user_scoped(
    api_client: tuple[AsyncClient, FinanceService],
) -> None:
    client, service = api_client
    first_user = await service.ensure_user(9002)
    second_user = await service.ensure_user(9003)
    payload = {"amount": "7.50", "category": "coffee"}

    unauthenticated = await client.post("/api/v1/expenses", json=payload)
    first = await client.post(
        "/api/v1/expenses",
        json=payload,
        headers={"X-API-Key": first_user.api_key or "", "Idempotency-Key": "shared-key-01"},
    )
    second = await client.post(
        "/api/v1/expenses",
        json=payload,
        headers={"X-API-Key": second_user.api_key or "", "Idempotency-Key": "shared-key-01"},
    )

    assert unauthenticated.status_code == 401
    assert first.status_code == 201
    assert second.status_code == 201
