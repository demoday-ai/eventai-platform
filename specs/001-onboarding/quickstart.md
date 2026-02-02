# Quickstart: Онбординг и выбор роли

**Feature**: 001-onboarding
**Date**: 2026-02-02

---

## Предварительные требования

- Python 3.12+
- Docker + Docker Compose (для PostgreSQL)
- Telegram Bot Token (через @BotFather)

## Настройка окружения

1. Скопировать `.env.example` в `.env` и заполнить:

```
DATABASE_URL=postgresql+asyncpg://demoday:demoday@localhost:5432/demoday
BOT_TOKEN=<ваш токен от @BotFather>
BOT_MODE=polling
ORGANIZER_TELEGRAM_IDS=123456789,987654321
```

2. Запустить PostgreSQL:

```bash
docker-compose up -d db
```

3. Установить зависимости:

```bash
cd backend
pip install -e ".[dev]"
```

4. Применить миграции (создание таблиц + seed-данные):

```bash
alembic upgrade head
```

5. Запустить бота:

```bash
python -m app.main
```

## Проверка работоспособности

### Тест 1: Первый вход (US-1)

1. Открыть бота в Telegram
2. Отправить `/start`
3. Ожидание: приветственное сообщение + 5 inline-кнопок
4. Нажать "Студент"
5. Ожидание: "Вы выбрали роль: Студент" + меню студента

### Тест 2: Подтип гостя (US-2)

1. Отправить `/role` → "Сменить роль"
2. Нажать "Гость"
3. Ожидание: экран выбора подтипа (3 кнопки)
4. Нажать "AI-практик"
5. Ожидание: подтверждение + меню гостя

### Тест 3: Whitelist организатора (US-1, SC-004)

1. Убедиться, что ваш Telegram ID НЕ в `ORGANIZER_TELEGRAM_IDS`
2. Отправить `/start` → нажать "Организатор"
3. Ожидание: "Роль организатора доступна только по приглашению"

### Тест 4: Смена роли (US-3)

1. Отправить `/start`
2. Ожидание: "Вы зарегистрированы как [роль]. Продолжить?"
3. Нажать "Сменить роль"
4. Выбрать другую роль
5. Ожидание: новая роль подтверждена

## Запуск автотестов

```bash
cd backend
pytest tests/ -v
```

## API-документация

После запуска: `http://localhost:8000/docs` (Swagger UI)
