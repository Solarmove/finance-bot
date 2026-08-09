from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from app.application.dto import CreateTransactionCommand
from app.application.services import FinanceService
from app.bot.chat import is_private_chat
from app.bot.parsing import CommandParseError, parse_transaction_command
from app.bot.views import (
    api_key_created,
    api_key_private_only,
    empty_history,
    help_message,
    monthly_balance,
    transaction_created,
    transaction_history,
    transaction_parse_error,
    unknown_message,
    welcome,
)
from app.core.config import Settings
from app.domain.enums import TransactionKind, TransactionSource
from app.infrastructure.telegram import RichMessageSender

router = Router(name=__name__)


async def _answer(message: Message, sender: RichMessageSender, html: str) -> None:
    await sender.send(
        chat_id=message.chat.id,
        html=html,
        message_thread_id=message.message_thread_id,
    )


async def _save_transaction(
    message: Message,
    finance_service: FinanceService,
    settings: Settings,
    kind: TransactionKind,
    rich_message_sender: RichMessageSender,
) -> None:
    if message.from_user is None or message.text is None:
        return
    try:
        parsed = parse_transaction_command(message.text, kind)
    except CommandParseError as error:
        command = "expense" if kind is TransactionKind.EXPENSE else "income"
        await _answer(
            message,
            rich_message_sender,
            transaction_parse_error(str(error), command),
        )
        return

    result = await finance_service.create_transaction(
        CreateTransactionCommand(
            telegram_user_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            kind=kind,
            amount=parsed.amount,
            currency=settings.default_currency,
            category=parsed.category,
            note=parsed.note,
            occurred_at=datetime.now(UTC),
            source=TransactionSource.TELEGRAM,
        )
    )
    await _answer(message, rich_message_sender, transaction_created(result.transaction))


@router.message(CommandStart())
async def start(
    message: Message,
    finance_service: FinanceService,
    rich_message_sender: RichMessageSender,
) -> None:
    if message.from_user is None:
        return
    registration = await finance_service.ensure_user(
        message.from_user.id, message.from_user.username, message.from_user.first_name
    )
    await _answer(
        message,
        rich_message_sender,
        welcome(registration.api_key, is_private_chat(message.chat.type)),
    )


@router.message(Command("help"))
async def help_command(message: Message, rich_message_sender: RichMessageSender) -> None:
    await _answer(message, rich_message_sender, help_message())


@router.message(Command("api_key"))
async def rotate_api_key(
    message: Message,
    finance_service: FinanceService,
    rich_message_sender: RichMessageSender,
) -> None:
    if message.from_user is None:
        return
    if not is_private_chat(message.chat.type):
        await _answer(message, rich_message_sender, api_key_private_only())
        return
    registration = await finance_service.ensure_user(
        message.from_user.id, message.from_user.username, message.from_user.first_name
    )
    is_rotation = registration.api_key is None
    api_key = (
        registration.api_key
        if registration.api_key
        else await finance_service.rotate_api_key(message.from_user.id)
    )
    await _answer(message, rich_message_sender, api_key_created(api_key, is_rotation))


@router.message(Command("expense"))
async def expense(
    message: Message,
    finance_service: FinanceService,
    settings: Settings,
    rich_message_sender: RichMessageSender,
) -> None:
    await _save_transaction(
        message, finance_service, settings, TransactionKind.EXPENSE, rich_message_sender
    )


@router.message(Command("income"))
async def income(
    message: Message,
    finance_service: FinanceService,
    settings: Settings,
    rich_message_sender: RichMessageSender,
) -> None:
    await _save_transaction(
        message, finance_service, settings, TransactionKind.INCOME, rich_message_sender
    )


@router.message(Command("balance"))
async def balance(
    message: Message,
    finance_service: FinanceService,
    settings: Settings,
    rich_message_sender: RichMessageSender,
) -> None:
    if message.from_user is None:
        return
    timezone = ZoneInfo(settings.app_timezone)
    now = datetime.now(timezone)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    summary = await finance_service.balance(
        message.from_user.id, month_start.astimezone(UTC), now.astimezone(UTC)
    )
    await _answer(
        message,
        rich_message_sender,
        monthly_balance(summary, settings.default_currency, now),
    )


@router.message(Command("history"))
async def history(
    message: Message,
    finance_service: FinanceService,
    settings: Settings,
    rich_message_sender: RichMessageSender,
) -> None:
    if message.from_user is None:
        return
    transactions = await finance_service.recent_transactions(message.from_user.id, limit=10)
    if not transactions:
        await _answer(message, rich_message_sender, empty_history())
        return
    await _answer(
        message,
        rich_message_sender,
        transaction_history(transactions, ZoneInfo(settings.app_timezone)),
    )


@router.message(F.text)
async def unknown_text(message: Message, rich_message_sender: RichMessageSender) -> None:
    await _answer(message, rich_message_sender, unknown_message())
