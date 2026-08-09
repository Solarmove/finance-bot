from datetime import UTC, datetime
from html import escape
from zoneinfo import ZoneInfo

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from app.application.dto import CreateTransactionCommand
from app.application.services import FinanceService
from app.bot.chat import is_private_chat
from app.bot.formatting import money, transaction_table
from app.bot.parsing import CommandParseError, parse_transaction_command
from app.core.config import Settings
from app.domain.enums import TransactionKind, TransactionSource

router = Router(name=__name__)


async def _save_transaction(
    message: Message,
    finance_service: FinanceService,
    settings: Settings,
    kind: TransactionKind,
) -> None:
    if message.from_user is None or message.text is None:
        return
    try:
        parsed = parse_transaction_command(message.text, kind)
    except CommandParseError as error:
        command = "expense" if kind is TransactionKind.EXPENSE else "income"
        await message.answer(
            f"<b>{escape(str(error))}</b>\n\nПример: <code>/{command} 125.50 продукты обед</code>"
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
    sign = "−" if kind is TransactionKind.EXPENSE else "+"
    title = "Расход записан" if kind is TransactionKind.EXPENSE else "Доход записан"
    await message.answer(
        f"<b>{title}</b>\n"
        f"<code>{sign}{result.transaction.amount:.2f} {result.transaction.currency}</code>\n"
        f"Категория: {escape(result.transaction.category)}"
    )


@router.message(CommandStart())
async def start(message: Message, finance_service: FinanceService) -> None:
    if message.from_user is None:
        return
    registration = await finance_service.ensure_user(
        message.from_user.id, message.from_user.username, message.from_user.first_name
    )
    text = (
        "<b>Финансовый помощник готов</b>\n\n"
        "Записывайте операции одной строкой:\n"
        "<code>/expense 420 транспорт такси</code>\n"
        "<code>/income 85000 зарплата август</code>\n\n"
        "<blockquote>Данные хранятся в PostgreSQL. Повторные API-запросы защищены "
        "ключом идемпотентности.</blockquote>\n"
        "Команда /help покажет все возможности."
    )
    if registration.api_key and is_private_chat(message.chat.type):
        text += (
            "\n\n<b>Ваш API-ключ</b> — сохраните его, повторно он не показывается:\n"
            f"<tg-spoiler><code>{registration.api_key}</code></tg-spoiler>"
        )
    elif registration.api_key:
        text += "\n\nПолучить API-ключ можно командой /api_key в личном чате с ботом."
    else:
        text += "\n\nПеревыпустить персональный ключ для HTTP API: /api_key."
    await message.answer(text)


@router.message(Command("help"))
async def help_command(message: Message) -> None:
    await message.answer(
        "<b>Команды</b>\n\n"
        "/expense <code>сумма категория комментарий</code>\n"
        "/income <code>сумма категория комментарий</code>\n"
        "/balance — итог текущего месяца\n"
        "/history — последние 10 операций\n\n"
        "/api_key — выпустить новый персональный API-ключ\n\n"
        "<blockquote expandable><b>Примеры</b>\n"
        "<code>/expense 89.90 продукты кофе</code>\n"
        "<code>/income 1500 фриланс логотип</code>\n"
        "Десятичный разделитель: точка или запятая.</blockquote>"
    )


@router.message(Command("api_key"))
async def rotate_api_key(message: Message, finance_service: FinanceService) -> None:
    if message.from_user is None:
        return
    if not is_private_chat(message.chat.type):
        await message.answer("API-ключ можно получить только в личном чате с ботом.")
        return
    registration = await finance_service.ensure_user(
        message.from_user.id, message.from_user.username, message.from_user.first_name
    )
    if registration.api_key:
        api_key = registration.api_key
        explanation = "Сохраните ключ — повторно он не показывается."
    else:
        api_key = await finance_service.rotate_api_key(message.from_user.id)
        explanation = "Предыдущий ключ отозван. Сохраните новый — повторно он не показывается."
    await message.answer(
        f"<b>Новый API-ключ</b>\n{explanation}\n\n<tg-spoiler><code>{api_key}</code></tg-spoiler>"
    )


@router.message(Command("expense"))
async def expense(message: Message, finance_service: FinanceService, settings: Settings) -> None:
    await _save_transaction(message, finance_service, settings, TransactionKind.EXPENSE)


@router.message(Command("income"))
async def income(message: Message, finance_service: FinanceService, settings: Settings) -> None:
    await _save_transaction(message, finance_service, settings, TransactionKind.INCOME)


@router.message(Command("balance"))
async def balance(message: Message, finance_service: FinanceService, settings: Settings) -> None:
    if message.from_user is None:
        return
    timezone = ZoneInfo(settings.app_timezone)
    now = datetime.now(timezone)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    summary = await finance_service.balance(
        message.from_user.id, month_start.astimezone(UTC), now.astimezone(UTC)
    )
    await message.answer(
        f"<b>Баланс за {now:%m.%Y}</b>\n\n"
        f"Доходы:  <code>+{money(summary.income, settings.default_currency)}</code>\n"
        f"Расходы: <code>−{money(summary.expense, settings.default_currency)}</code>\n"
        f"<blockquote>Итого: <b>{escape(money(summary.net, settings.default_currency))}</b>"
        "</blockquote>"
    )


@router.message(Command("history"))
async def history(message: Message, finance_service: FinanceService, settings: Settings) -> None:
    if message.from_user is None:
        return
    transactions = await finance_service.recent_transactions(message.from_user.id, limit=10)
    if not transactions:
        await message.answer("Операций пока нет. Добавьте первую через /expense или /income.")
        return
    await message.answer(
        f"<b>Последние операции</b>\n"
        f"{transaction_table(transactions, ZoneInfo(settings.app_timezone))}"
    )


@router.message(F.text)
async def unknown_text(message: Message) -> None:
    await message.answer("Не понял сообщение. Используйте /help, чтобы увидеть команды.")
