from datetime import datetime
from zoneinfo import ZoneInfo

from app.application.dto import Balance, TransactionDTO
from app.bot.formatting import money
from app.domain.enums import TransactionKind
from app.infrastructure.telegram.markdown import escape_markdown, escape_table_cell


def transaction_parse_error(message: str, command: str) -> str:
    return (
        "### ⚠️ Не удалось записать операцию\n\n"
        f"{escape_markdown(message)}\n\n"
        "#### Правильный формат\n\n"
        f"`/{command} 125.50 продукты обед`\n\n"
        "> Сумму можно вводить через точку или запятую."
    )


def transaction_created(transaction: TransactionDTO) -> str:
    is_expense = transaction.kind is TransactionKind.EXPENSE
    title = "Расход записан" if is_expense else "Доход записан"
    icon = "📉" if is_expense else "📈"
    sign = "−" if is_expense else "+"
    rows = [
        f"| **Сумма** | **{sign}{transaction.amount:.2f} {transaction.currency}** |",
        f"| **Категория** | {escape_table_cell(transaction.category)} |",
    ]
    if transaction.note:
        rows.append(f"| **Комментарий** | {escape_table_cell(transaction.note)} |")
    return (
        f"## {icon} {title}\n\n"
        "| | |\n"
        "|:--|--:|\n"
        f"{'\n'.join(rows)}\n\n"
        "_Операция учтена в текущем балансе._"
    )


def welcome(api_key: str | None, can_show_key: bool) -> str:
    if api_key and can_show_key:
        api_section = (
            "### 🔐 Ключ для HTTP API\n\n"
            "Сохраните его сейчас — в базе хранится только хеш.\n\n"
            f"||`{api_key}`||"
        )
    elif api_key:
        api_section = "### 🔐 HTTP API\n\nПолучить ключ можно командой `/api_key` в личном чате."
    else:
        api_section = "### 🔐 HTTP API\n\nУправление персональным ключом: `/api_key`."

    return (
        "# 💰 Личные финансы\n\n"
        "Доходы и расходы — без сложных форм и лишних экранов.\n\n"
        "---\n\n"
        "### Быстрый старт\n\n"
        "1. Расход: `/expense 420 транспорт такси`\n"
        "2. Доход: `/income 85000 зарплата август`\n"
        "3. Итоги месяца: `/balance`\n\n"
        f"{api_section}\n\n"
        "_Все операции сохраняются в PostgreSQL._"
    )


def help_message() -> str:
    return (
        "# 🧭 Возможности\n\n"
        "| Команда | Что делает |\n"
        "|:--|:--|\n"
        "| `/expense` | Добавляет расход |\n"
        "| `/income` | Добавляет доход |\n"
        "| `/balance` | Показывает итог месяца |\n"
        "| `/history` | Открывает историю операций |\n"
        "| `/api_key` | Перевыпускает API-ключ |\n\n"
        "### Примеры\n\n"
        "- `/expense 89.90 продукты кофе`\n"
        "- `/income 1500 фриланс логотип`\n\n"
        "> Комментарий после категории необязателен."
    )


def api_key_private_only() -> str:
    return (
        "### 🔒 Нужен личный чат\n\n"
        "API-ключ открывает доступ к вашим финансовым операциям, поэтому бот выдаёт его "
        "только в личном диалоге."
    )


def api_key_created(api_key: str, is_rotation: bool) -> str:
    explanation = (
        "Предыдущий ключ уже отозван. Обновите его во всех интеграциях."
        if is_rotation
        else "Сохраните ключ сейчас — повторно он не показывается."
    )
    return (
        "## 🔐 Новый API-ключ\n\n"
        f"{explanation}\n\n"
        f"> ||`{api_key}`||\n\n"
        "_Передавайте ключ только в заголовке `X-API-Key`._"
    )


def monthly_balance(summary: Balance, currency: str, now: datetime) -> str:
    net_icon = "🟢" if summary.net >= 0 else "🔴"
    return (
        f"# 📊 Итоги за {now:%m.%Y}\n\n"
        "| Показатель | Сумма |\n"
        "|:--|--:|\n"
        f"| 📈 Доходы | **+{money(summary.income, currency)}** |\n"
        f"| 📉 Расходы | −{money(summary.expense, currency)} |\n"
        f"| **{net_icon} Остаток** | **{money(summary.net, currency)}** |\n\n"
        "_Период: с первого дня месяца по текущий момент._"
    )


def transaction_history(transactions: list[TransactionDTO], timezone: ZoneInfo) -> str:
    rows: list[str] = []
    for transaction in transactions:
        is_expense = transaction.kind is TransactionKind.EXPENSE
        operation = "Расход" if is_expense else "Доход"
        sign = "−" if is_expense else "+"
        local_time = transaction.occurred_at.astimezone(timezone)
        rows.append(
            f"| {local_time:%d.%m.%y} | {operation} | "
            f"{escape_table_cell(transaction.category)} | "
            f"**{sign}{transaction.amount:.2f} {transaction.currency}** |"
        )
    return (
        "# 🧾 История операций\n\n"
        f"_Последние {len(transactions)} операций_\n\n"
        "| Дата | Тип | Категория | Сумма |\n"
        "|:--|:--|:--|--:|\n"
        f"{'\n'.join(rows)}\n\n"
        f"> Часовой пояс: {escape_markdown(str(timezone))}"
    )


def empty_history() -> str:
    return (
        "## 🧾 История пока пуста\n\n"
        "Добавьте первую операцию:\n\n"
        "- `/expense 100 продукты`\n"
        "- `/income 1000 зарплата`"
    )


def unknown_message() -> str:
    return "### 🤔 Не понял сообщение\n\nОтправьте `/help`, чтобы посмотреть команды и примеры."
