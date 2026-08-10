import hashlib

from fastapi import APIRouter, HTTPException, Response, status

from app.api.di import (
    CurrentUser,
    FinanceServiceDep,
    IdempotencyKey,
    NotifierDep,
    ReadinessCheckerDep,
    SettingsDep,
)
from app.api.dto import (
    ExpenseCreate,
    ExpenseResponse,
    LivenessResponse,
    ReadinessResponse,
)
from app.application.dto import CreateTransactionCommand
from app.domain.enums import TransactionKind, TransactionSource

router = APIRouter()


@router.post(
    "/api/v1/expenses",
    response_model=ExpenseResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_200_OK: {"description": "Expense already exists"},
        status.HTTP_401_UNAUTHORIZED: {"description": "Invalid API key"},
        status.HTTP_422_UNPROCESSABLE_CONTENT: {"description": "Validation failed"},
    },
)
async def create_expense(
    payload: ExpenseCreate,
    user: CurrentUser,
    service: FinanceServiceDep,
    settings: SettingsDep,
    notifier: NotifierDep,
    idempotency_key: IdempotencyKey,
) -> ExpenseResponse:
    if payload.currency != settings.default_currency:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Only {settings.default_currency} currency is currently supported",
        )

    key_digest = hashlib.sha256(idempotency_key.encode()).hexdigest()
    external_id = f"api:{user.id.hex}:{key_digest}"
    result = await service.create_transaction(
        CreateTransactionCommand(
            telegram_user_id=user.telegram_user_id,
            kind=TransactionKind.EXPENSE,
            amount=payload.amount,
            currency=payload.currency,
            category=payload.category or "",
            note=payload.note,
            occurred_at=payload.occurred_at,
            source=TransactionSource.API,
            external_id=external_id,
        )
    )

    if payload.notify and result.created:
        await notifier.expense_created(user.telegram_user_id, result.transaction)

    return ExpenseResponse(
        id=result.transaction.id,
        status="created" if result.created else "already_exists",
        amount=result.transaction.amount,
        currency=result.transaction.currency,
        category=result.transaction.category,
        occurred_at=result.transaction.occurred_at,
    )


@router.get("/health/live", response_model=LivenessResponse)
async def live() -> LivenessResponse:
    return LivenessResponse(status="ok")


@router.get("/health/ready", response_model=ReadinessResponse)
async def ready(response: Response, checker: ReadinessCheckerDep) -> ReadinessResponse:
    result = await checker.check()
    if not result.is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return ReadinessResponse(
        status="ok" if result.is_ready else "unavailable",
        checks=result.checks,
    )
