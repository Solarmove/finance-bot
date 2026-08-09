import secrets
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import structlog
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import BotCommand, Update
from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, status
from pydantic import ValidationError
from redis.asyncio import Redis

from app.api.handlers import router as api_router
from app.application.services import FinanceService
from app.application.uow import SqlAlchemyUnitOfWork
from app.bot.handlers import router as bot_router
from app.core.config import Settings
from app.infrastructure.database import create_engine, create_session_factory
from app.infrastructure.health import ReadinessChecker
from app.infrastructure.notifications import TelegramTransactionNotifier

logger = structlog.get_logger()


def create_application(settings: Settings) -> FastAPI:
    engine = create_engine(settings.database_url)
    session_factory = create_session_factory(engine)
    finance_service = FinanceService(
        uow_factory=lambda: SqlAlchemyUnitOfWork(session_factory),
        default_timezone=settings.app_timezone,
    )
    redis = Redis.from_url(settings.redis_url)
    storage = RedisStorage(redis=redis)
    dispatcher = Dispatcher(storage=storage)
    dispatcher.include_router(bot_router)
    dispatcher["finance_service"] = finance_service
    dispatcher["settings"] = settings
    bot = Bot(
        token=settings.bot_token.get_secret_value(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML, link_preview_is_disabled=True),
    )
    transaction_notifier = TelegramTransactionNotifier(bot)
    readiness_checker = ReadinessChecker(engine, redis)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        await dispatcher.emit_startup(bot=bot)
        await bot.set_my_commands(
            [
                BotCommand(command="expense", description="Добавить расход"),
                BotCommand(command="income", description="Добавить доход"),
                BotCommand(command="balance", description="Баланс за месяц"),
                BotCommand(command="history", description="Последние операции"),
                BotCommand(command="api_key", description="Перевыпустить API-ключ"),
                BotCommand(command="help", description="Справка"),
            ]
        )
        await bot.set_webhook(
            url=settings.webhook_url,
            secret_token=settings.webhook_secret.get_secret_value(),
            allowed_updates=dispatcher.resolve_used_update_types(),
            drop_pending_updates=settings.drop_pending_updates,
        )
        logger.info("webhook_configured", url=settings.webhook_url)
        try:
            yield
        finally:
            await dispatcher.emit_shutdown(bot=bot)
            await dispatcher.storage.close()
            await bot.session.close()
            await engine.dispose()

    app = FastAPI(
        title="Finance Bot API",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.finance_service = finance_service
    app.state.bot = bot
    app.state.engine = engine
    app.state.redis = redis
    app.state.transaction_notifier = transaction_notifier
    app.state.readiness_checker = readiness_checker
    app.include_router(api_router)

    @app.post(settings.webhook_path, include_in_schema=False)
    async def telegram_webhook(
        payload: dict[str, Any],
        background_tasks: BackgroundTasks,
        x_telegram_secret: str | None = Header(
            default=None, alias="X-Telegram-Bot-Api-Secret-Token"
        ),
    ) -> dict[str, bool]:
        expected = settings.webhook_secret.get_secret_value()
        if x_telegram_secret is None or not secrets.compare_digest(x_telegram_secret, expected):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
        try:
            update = Update.model_validate(payload, context={"bot": bot})
        except ValidationError as error:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid Telegram update"
            ) from error
        background_tasks.add_task(dispatcher.feed_update, bot, update)
        return {"ok": True}

    return app
