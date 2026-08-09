from datetime import datetime
from html import escape
from zoneinfo import ZoneInfo

from app.application.dto import Balance, TransactionDTO
from app.bot.formatting import money
from app.domain.enums import TransactionKind


def transaction_parse_error(message: str, command: str) -> str:
    return (
        "<h3>⚠️ Не удалось записать операцию</h3>"
        f"<p>{escape(message)}</p>"
        "<details open><summary>Правильный формат</summary>"
        f"<p><code>/{command} 125.50 продукты обед</code></p>"
        "<footer>Сумму можно вводить через точку или запятую.</footer>"
        "</details>"
    )


def transaction_created(transaction: TransactionDTO) -> str:
    is_expense = transaction.kind is TransactionKind.EXPENSE
    title = "Расход записан" if is_expense else "Доход записан"
    icon = "📉" if is_expense else "📈"
    sign = "−" if is_expense else "+"
    note_row = (
        f'<tr><th align="left">Комментарий</th><td>{escape(transaction.note)}</td></tr>'
        if transaction.note
        else ""
    )
    return (
        f"<h2>{icon} {title}</h2>"
        "<table bordered>"
        f'<tr><th align="left">Сумма</th><td align="right"><b>{sign}'
        f"{transaction.amount:.2f} {transaction.currency}</b></td></tr>"
        f'<tr><th align="left">Категория</th><td>{escape(transaction.category)}</td></tr>'
        f"{note_row}"
        "</table>"
        "<footer>Операция учтена в текущем балансе.</footer>"
    )


def welcome(api_key: str | None, can_show_key: bool) -> str:
    api_section: str
    if api_key and can_show_key:
        api_section = (
            "<details><summary>🔐 Ваш ключ для HTTP API</summary>"
            "<p>Сохраните его сейчас — в базе хранится только хеш.</p>"
            f"<p><tg-spoiler><code>{api_key}</code></tg-spoiler></p>"
            "</details>"
        )
    elif api_key:
        api_section = (
            "<p>🔐 Получить ключ для HTTP API можно командой "
            "<code>/api_key</code> в личном чате.</p>"
        )
    else:
        api_section = "<p>🔐 Управление ключом для HTTP API: <code>/api_key</code>.</p>"

    return (
        "<h1>💰 Личные финансы</h1>"
        "<p>Доходы и расходы — без сложных форм и лишних экранов.</p>"
        "<hr/>"
        "<h3>Быстрый старт</h3>"
        "<ol>"
        "<li>Расход: <code>/expense 420 транспорт такси</code></li>"
        "<li>Доход: <code>/income 85000 зарплата август</code></li>"
        "<li>Итоги месяца: <code>/balance</code></li>"
        "</ol>"
        f"{api_section}"
        "<footer>Все операции сохраняются в PostgreSQL.</footer>"
    )


def help_message() -> str:
    return (
        "<h1>🧭 Возможности</h1>"
        "<table bordered striped>"
        "<tr><th>Команда</th><th>Что делает</th></tr>"
        "<tr><td><code>/expense</code></td><td>Добавляет расход</td></tr>"
        "<tr><td><code>/income</code></td><td>Добавляет доход</td></tr>"
        "<tr><td><code>/balance</code></td><td>Показывает итог месяца</td></tr>"
        "<tr><td><code>/history</code></td><td>Открывает историю операций</td></tr>"
        "<tr><td><code>/api_key</code></td><td>Перевыпускает API-ключ</td></tr>"
        "</table>"
        "<details><summary>Примеры операций</summary>"
        "<ul>"
        "<li><code>/expense 89.90 продукты кофе</code></li>"
        "<li><code>/income 1500 фриланс логотип</code></li>"
        "</ul>"
        "<p>Комментарий после категории необязателен.</p>"
        "</details>"
    )


def api_key_private_only() -> str:
    return (
        "<h3>🔒 Нужен личный чат</h3>"
        "<p>API-ключ содержит доступ к вашим финансовым операциям, поэтому бот выдаёт его "
        "только в личном диалоге.</p>"
    )


def api_key_created(api_key: str, is_rotation: bool) -> str:
    explanation = (
        "Предыдущий ключ уже отозван. Обновите его во всех интеграциях."
        if is_rotation
        else "Сохраните ключ сейчас — повторно он не показывается."
    )
    return (
        "<h2>🔐 Новый API-ключ</h2>"
        f"<p>{explanation}</p>"
        f"<blockquote><tg-spoiler><code>{api_key}</code></tg-spoiler></blockquote>"
        "<footer>Передавайте ключ только в заголовке X-API-Key.</footer>"
    )


def monthly_balance(summary: Balance, currency: str, now: datetime) -> str:
    net_icon = "🟢" if summary.net >= 0 else "🔴"
    return (
        f"<h1>📊 Итоги за {now:%m.%Y}</h1>"
        "<table bordered striped>"
        '<tr><th align="left">Показатель</th><th align="right">Сумма</th></tr>'
        '<tr><td>📈 Доходы</td><td align="right"><b>+'
        f"{money(summary.income, currency)}</b></td></tr>"
        f'<tr><td>📉 Расходы</td><td align="right">−{money(summary.expense, currency)}</td></tr>'
        f'<tr><th align="left">{net_icon} Остаток</th>'
        f'<th align="right">{money(summary.net, currency)}</th></tr>'
        "</table>"
        "<footer>Период: с первого дня месяца по текущий момент.</footer>"
    )


def transaction_history(transactions: list[TransactionDTO], timezone: ZoneInfo) -> str:
    rows: list[str] = []
    for transaction in transactions:
        is_expense = transaction.kind is TransactionKind.EXPENSE
        operation = "Расход" if is_expense else "Доход"
        sign = "−" if is_expense else "+"
        local_time = transaction.occurred_at.astimezone(timezone)
        rows.append(
            "<tr>"
            f"<td>{local_time:%d.%m.%y}</td>"
            f"<td>{operation}</td>"
            f"<td>{escape(transaction.category)}</td>"
            f'<td align="right"><b>{sign}{transaction.amount:.2f} '
            f"{transaction.currency}</b></td>"
            "</tr>"
        )
    return (
        "<h1>🧾 История операций</h1>"
        "<table bordered striped>"
        f"<caption>Последние {len(transactions)} операций</caption>"
        '<tr><th>Дата</th><th>Тип</th><th>Категория</th><th align="right">Сумма</th></tr>'
        f"{''.join(rows)}"
        "</table>"
        f"<footer>Часовой пояс: {escape(str(timezone))}</footer>"
    )


def empty_history() -> str:
    return (
        "<h2>🧾 История пока пуста</h2>"
        "<p>Добавьте первую операцию:</p>"
        "<ul><li><code>/expense 100 продукты</code></li>"
        "<li><code>/income 1000 зарплата</code></li></ul>"
    )


def unknown_message() -> str:
    return (
        "<h3>🤔 Не понял сообщение</h3>"
        "<p>Отправьте <code>/help</code>, чтобы посмотреть команды и примеры.</p>"
    )
