from typing import Annotated, cast

from fastapi import Depends, Request

from app.application.notifications import TransactionNotifier
from app.application.services import FinanceService
from app.core.config import Settings
from app.infrastructure.health import ReadinessChecker


def get_settings(request: Request) -> Settings:
    return cast(Settings, request.app.state.settings)


def get_finance_service(request: Request) -> FinanceService:
    return cast(FinanceService, request.app.state.finance_service)


def get_notifier(request: Request) -> TransactionNotifier:
    return cast(TransactionNotifier, request.app.state.transaction_notifier)


def get_readiness_checker(request: Request) -> ReadinessChecker:
    return cast(ReadinessChecker, request.app.state.readiness_checker)


SettingsDep = Annotated[Settings, Depends(get_settings)]
FinanceServiceDep = Annotated[FinanceService, Depends(get_finance_service)]
NotifierDep = Annotated[TransactionNotifier, Depends(get_notifier)]
ReadinessCheckerDep = Annotated[ReadinessChecker, Depends(get_readiness_checker)]
