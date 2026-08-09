from collections.abc import Awaitable
from typing import cast

import structlog
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.application.dto import ReadinessResult

logger = structlog.get_logger()


class ReadinessChecker:
    def __init__(self, engine: AsyncEngine, redis: Redis) -> None:
        self._engine = engine
        self._redis = redis

    async def check(self) -> ReadinessResult:
        checks = {
            "postgres": await self._check_postgres(),
            "redis": await self._check_redis(),
        }
        return ReadinessResult(checks=checks)

    async def _check_postgres(self) -> str:
        try:
            async with self._engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
            return "ok"
        except Exception:
            logger.warning("postgres_readiness_failed", exc_info=True)
            return "unavailable"

    async def _check_redis(self) -> str:
        try:
            await cast(Awaitable[bool], self._redis.ping())
            return "ok"
        except Exception:
            logger.warning("redis_readiness_failed", exc_info=True)
            return "unavailable"
