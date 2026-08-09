# Finance Bot

Telegram-бот для учёта расходов и доходов. Работает только через webhook, принимает расходы
через JSON API на FastAPI и использует PostgreSQL, Redis, SQLAlchemy async, Pydantic и паттерн
Unit of Work. Runtime проекта — Python 3.14.

## Что умеет

- `/expense 420 транспорт такси` — записать расход;
- `/income 85000 зарплата август` — записать доход;
- `/balance` — показать доходы, расходы и итог текущего месяца;
- `/history` — показать последние операции в моноширинной таблице;
- `/api_key` — перевыпустить персональный API-ключ;
- `POST /api/v1/expenses` — создать расход из внешней системы;
- `/docs` и `/redoc` — интерактивная OpenAPI-документация FastAPI;
- идемпотентность API через обязательный `Idempotency-Key`;
- liveness/readiness endpoints и структурированные JSON-логи.

Бот использует Rich Markdown из Bot API 10.2 через нативные `InputRichMessage` и
`Bot.send_rich_message()` из aiogram 3.30: GFM-таблицы, заголовки, списки, цитаты и
spoiler-разметку. В Telegram handlers используется нативный shortcut `Message.answer_rich()`.
Если Telegram отклоняет rich-сообщение, бот автоматически повторяет отправку через обычный
`Message.answer()` без `parse_mode`.

## Персональные API-ключи

При первом `/start` создаётся ключ вида `fb_<prefix>_<secret>`. Открытый ключ показывается
только один раз и только в личном чате. В PostgreSQL хранится SHA-256-хеш, а не сам ключ.
Команда `/api_key` немедленно отзывает старый ключ и выдаёт новый.

Ключ однозначно определяет пользователя, поэтому `telegram_user_id` в JSON передавать нельзя.
Все операции пока ведутся в одной валюте из `DEFAULT_CURRENCY`; API отклонит другую валюту,
чтобы баланс не складывал несопоставимые суммы без курса конвертации.

```http
POST /api/v1/expenses HTTP/1.1
Host: bot.example.com
Content-Type: application/json
X-API-Key: fb_012345abcdef_replace_with_real_secret
Idempotency-Key: bank-event-2026-08-09-0001

{
  "amount": "129.90",
  "currency": "PLN",
  "category": "Продукты",
  "note": "Супермаркет",
  "occurred_at": "2026-08-09T14:35:00+02:00",
  "notify": true
}
```

Первый запрос возвращает `201 Created`, повтор с тем же `Idempotency-Key` — `200 OK` и
`"status": "already_exists"`. Заголовок идемпотентности должен содержать 8–120 символов.

Пример с `curl`:

```bash
curl -X POST https://bot.example.com/api/v1/expenses \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $FINANCE_BOT_API_KEY" \
  -H "Idempotency-Key: bank-event-2026-08-09-0001" \
  -d '{"amount":"129.90","currency":"PLN","category":"Продукты"}'
```

## Запуск

Требуются публичный HTTPS-домен и reverse proxy, который направляет запросы на порт `8080`.
Telegram не принимает обычный HTTP webhook. Создайте бота через BotFather и затем:

```bash
cp .env.example .env
# заполните BOT_TOKEN, WEBHOOK_BASE_URL и WEBHOOK_SECRET
docker compose up --build -d
```

При старте контейнер применяет Alembic-миграции и регистрирует webhook. Проверка состояния:

```bash
curl http://localhost:8080/health/live
curl http://localhost:8080/health/ready
```

Для локальной разработки без Docker:

```bash
uv sync --dev
uv run alembic upgrade head
uv run python -m app.main
```

Webhook URL должен быть доступен Telegram извне, например через Caddy, nginx или туннель.
Заголовок `X-Telegram-Bot-Api-Secret-Token` проверяется обработчиком aiogram.

## Проверки

```bash
uv run ruff check .
uv run mypy app
uv run pytest
```

## Структура

```text
app/
├── api/              # FastAPI transport
│   ├── di/           # зависимости FastAPI: container, auth, headers
│   └── dto/          # HTTP request/response DTO
├── application/      # use cases, contracts, Unit of Work и application DTO
├── bot/              # тонкие aiogram routes, controllers, parsing, DTO и views
├── core/             # configuration and logging
├── domain/           # enums and domain vocabulary
└── infrastructure/   # SQLAlchemy, repositories, notifier и readiness checker
migrations/           # Alembic schema migrations
tests/                # unit/integration tests on async SQLite
```

Каждый метод `FinanceService` создаёт собственный Unit of Work и `AsyncSession`; сессии не
разделяются между конкурентными webhook/API-задачами.
