import hashlib
import secrets
from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.exc import IntegrityError

from app.application.dto import (
    Balance,
    CreateTransactionCommand,
    CreateTransactionResult,
    EnsureUserResult,
    TransactionDTO,
    UserDTO,
)
from app.application.uow import AbstractUnitOfWork
from app.domain.enums import TransactionKind
from app.infrastructure.models import Transaction, User


class FinanceService:
    def __init__(
        self,
        uow_factory: Callable[[], AbstractUnitOfWork],
        default_timezone: str,
    ) -> None:
        self._uow_factory = uow_factory
        self._default_timezone = default_timezone

    async def ensure_user(
        self,
        telegram_user_id: int,
        username: str | None = None,
        first_name: str | None = None,
    ) -> EnsureUserResult:
        async with self._uow_factory() as uow:
            user = await uow.users.get_by_telegram_id(telegram_user_id)
            api_key: str | None = None
            if user is None:
                api_key, prefix, key_hash = self._generate_api_key()
                user = User(
                    telegram_user_id=telegram_user_id,
                    username=username,
                    first_name=first_name,
                    timezone=self._default_timezone,
                    api_key_prefix=prefix,
                    api_key_hash=key_hash,
                )
                uow.users.add(user)
            else:
                user.username = username or user.username
                user.first_name = first_name or user.first_name
            await uow.commit()
            return EnsureUserResult(user=self._to_user_dto(user), api_key=api_key)

    async def rotate_api_key(self, telegram_user_id: int) -> str:
        async with self._uow_factory() as uow:
            user = await uow.users.get_by_telegram_id(telegram_user_id)
            if user is None:
                raise LookupError("User is not registered")
            api_key, prefix, key_hash = self._generate_api_key()
            user.api_key_prefix = prefix
            user.api_key_hash = key_hash
            await uow.commit()
            return api_key

    async def authenticate_api_key(self, api_key: str) -> UserDTO | None:
        prefix = self._extract_api_key_prefix(api_key)
        if prefix is None:
            return None
        async with self._uow_factory() as uow:
            user = await uow.users.get_by_api_key_prefix(prefix)
            if user is None:
                return None
            supplied_hash = hashlib.sha256(api_key.encode()).hexdigest()
            if not secrets.compare_digest(supplied_hash, user.api_key_hash):
                return None
            return self._to_user_dto(user)

    async def create_transaction(
        self, command: CreateTransactionCommand
    ) -> CreateTransactionResult:
        try:
            async with self._uow_factory() as uow:
                if command.external_id:
                    existing = await uow.transactions.get_by_external_id(command.external_id)
                    if existing is not None:
                        return CreateTransactionResult(
                            self._to_transaction_dto(existing), created=False
                        )

                user = await uow.users.get_by_telegram_id(command.telegram_user_id)
                if user is None:
                    _, prefix, key_hash = self._generate_api_key()
                    user = User(
                        telegram_user_id=command.telegram_user_id,
                        username=command.username,
                        first_name=command.first_name,
                        timezone=self._default_timezone,
                        api_key_prefix=prefix,
                        api_key_hash=key_hash,
                    )
                    uow.users.add(user)

                transaction = Transaction(
                    user=user,
                    kind=command.kind,
                    amount=command.amount.quantize(Decimal("0.01")),
                    currency=command.currency.upper(),
                    category=command.category,
                    note=command.note,
                    occurred_at=command.occurred_at,
                    source=command.source,
                    external_id=command.external_id,
                )
                uow.transactions.add(transaction)
                await uow.commit()
                return CreateTransactionResult(self._to_transaction_dto(transaction), created=True)
        except IntegrityError:
            if command.external_id:
                recovered = await self.transaction_by_external_id(command.external_id)
                if recovered is not None:
                    return CreateTransactionResult(recovered, created=False)
            raise

    async def recent_transactions(
        self, telegram_user_id: int, limit: int = 10
    ) -> list[TransactionDTO]:
        async with self._uow_factory() as uow:
            user = await uow.users.get_by_telegram_id(telegram_user_id)
            if user is None:
                return []
            transactions = await uow.transactions.list_recent(user.id, limit)
            return [self._to_transaction_dto(transaction) for transaction in transactions]

    async def transaction_by_external_id(self, external_id: str) -> TransactionDTO | None:
        async with self._uow_factory() as uow:
            transaction = await uow.transactions.get_by_external_id(external_id)
            return self._to_transaction_dto(transaction) if transaction else None

    async def balance(
        self, telegram_user_id: int, start: datetime, end: datetime | None = None
    ) -> Balance:
        async with self._uow_factory() as uow:
            user = await uow.users.get_by_telegram_id(telegram_user_id)
            if user is None:
                return Balance(Decimal("0"), Decimal("0"))
            totals = await uow.transactions.totals(user.id, start, end or datetime.now(UTC))
            return Balance(
                income=totals[TransactionKind.INCOME],
                expense=totals[TransactionKind.EXPENSE],
            )

    @staticmethod
    def _generate_api_key() -> tuple[str, str, str]:
        prefix = secrets.token_hex(6)
        api_key = f"fb_{prefix}_{secrets.token_urlsafe(32)}"
        return api_key, prefix, hashlib.sha256(api_key.encode()).hexdigest()

    @staticmethod
    def _extract_api_key_prefix(api_key: str) -> str | None:
        parts = api_key.split("_", maxsplit=2)
        if len(parts) != 3 or parts[0] != "fb" or len(parts[1]) != 12 or not parts[2]:
            return None
        return parts[1]

    @staticmethod
    def _to_user_dto(user: User) -> UserDTO:
        return UserDTO(
            id=user.id,
            telegram_user_id=user.telegram_user_id,
            username=user.username,
            first_name=user.first_name,
            timezone=user.timezone,
        )

    @staticmethod
    def _to_transaction_dto(transaction: Transaction) -> TransactionDTO:
        return TransactionDTO(
            id=transaction.id,
            kind=transaction.kind,
            amount=transaction.amount,
            currency=transaction.currency,
            category=transaction.category,
            note=transaction.note,
            occurred_at=transaction.occurred_at,
            source=transaction.source,
            external_id=transaction.external_id,
        )
