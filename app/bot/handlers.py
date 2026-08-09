from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from app.bot.controllers import (
    AccountController,
    ReportController,
    StaticController,
    TransactionController,
)
from app.domain.enums import TransactionKind

router = Router(name=__name__)


@router.message(CommandStart())
async def start(message: Message, account_controller: AccountController) -> None:
    await account_controller.start(message)


@router.message(Command("help"))
async def help_command(message: Message, static_controller: StaticController) -> None:
    await static_controller.help(message)


@router.message(Command("api_key"))
async def rotate_api_key(message: Message, account_controller: AccountController) -> None:
    await account_controller.rotate_api_key(message)


@router.message(Command("expense"))
async def expense(message: Message, transaction_controller: TransactionController) -> None:
    await transaction_controller.record(message, TransactionKind.EXPENSE)


@router.message(Command("income"))
async def income(message: Message, transaction_controller: TransactionController) -> None:
    await transaction_controller.record(message, TransactionKind.INCOME)


@router.message(Command("balance"))
async def balance(message: Message, report_controller: ReportController) -> None:
    await report_controller.balance(message)


@router.message(Command("history"))
async def history(message: Message, report_controller: ReportController) -> None:
    await report_controller.history(message)


@router.message(F.text)
async def unknown_text(message: Message, static_controller: StaticController) -> None:
    await static_controller.unknown(message)
