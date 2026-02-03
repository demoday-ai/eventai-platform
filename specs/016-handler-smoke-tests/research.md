# Research: Smoke-тесты на критичные хендлеры

**Date**: 2026-02-03
**Feature**: 016-handler-smoke-tests

---

## 1. Mocking python-telegram-bot 21.x

### Decision: Использовать `Update.de_json()` + mock bot

**Rationale**: PTB 21.x использует immutable объекты. `de_json()` — официальный способ создания Update из словаря.

**Alternatives considered**:
- `ptbtest` library — устарела, не поддерживает PTB 21.x полностью
- Прямое создание через конструктор — работает, но менее удобно

### Паттерн создания mock Update

```python
from telegram import Update

def make_message_update(
    user_id: int,
    chat_id: int,
    text: str,
    update_id: int = 1,
    message_id: int = 1,
) -> dict:
    """Create update dict for message."""
    return {
        "update_id": update_id,
        "message": {
            "message_id": message_id,
            "date": 1234567890,
            "chat": {"id": chat_id, "type": "private"},
            "from": {"id": user_id, "is_bot": False, "first_name": "Test"},
            "text": text,
        },
    }

def make_callback_update(
    user_id: int,
    chat_id: int,
    callback_data: str,
    update_id: int = 1,
) -> dict:
    """Create update dict for callback query."""
    return {
        "update_id": update_id,
        "callback_query": {
            "id": f"query_{update_id}",
            "from": {"id": user_id, "is_bot": False, "first_name": "Test"},
            "chat_instance": str(chat_id),
            "data": callback_data,
            "message": {
                "message_id": 1,
                "date": 1234567890,
                "chat": {"id": chat_id, "type": "private"},
            },
        },
    }

# Usage
update = Update.de_json(make_message_update(123, 456, "/start"), bot)
```

---

## 2. Async Testing with pytest-asyncio

### Decision: pytest + pytest-asyncio + Application.process_update()

**Rationale**:
- `process_update()` позволяет тестировать хендлеры изолированно
- Не требует реального Bot Token (bot не отправляет сообщения при тестировании)

### Паттерн тестирования

```python
import pytest
from telegram.ext import ApplicationBuilder

@pytest.fixture
async def app():
    """Create test application."""
    application = ApplicationBuilder().token("TEST:TOKEN").build()
    # Register handlers from our app
    from app.bot.handlers import onboarding
    onboarding.register_handlers(application)

    await application.initialize()
    yield application
    await application.shutdown()

@pytest.mark.asyncio
async def test_start_command(app):
    update_dict = make_message_update(user_id=123, chat_id=123, text="/start")
    update = Update.de_json(update_dict, app.bot)

    await app.process_update(update)

    # Assert: check database state, context.user_data, etc.
```

---

## 3. Mocking Bot Responses

### Decision: Mock `bot.send_message` и `query.answer`

**Rationale**: Мы не хотим отправлять реальные сообщения. Mock позволяет проверить что бот "отправил" правильные данные.

### Паттерн

```python
from unittest.mock import AsyncMock, patch

@pytest.fixture
def mock_bot_methods():
    """Mock bot methods to capture responses."""
    with patch.object(Bot, "send_message", new_callable=AsyncMock) as send_msg, \
         patch.object(Bot, "edit_message_text", new_callable=AsyncMock) as edit_msg, \
         patch.object(Bot, "answer_callback_query", new_callable=AsyncMock) as answer:

        # Return mock objects for assertions
        yield {
            "send_message": send_msg,
            "edit_message_text": edit_msg,
            "answer_callback_query": answer,
        }

@pytest.mark.asyncio
async def test_onboarding_sends_welcome(app, mock_bot_methods):
    update = Update.de_json(make_message_update(123, 123, "/start"), app.bot)
    await app.process_update(update)

    # Assert welcome message was sent
    mock_bot_methods["send_message"].assert_called_once()
    call_args = mock_bot_methods["send_message"].call_args
    assert "Добро пожаловать" in call_args.kwargs.get("text", "")
```

---

## 4. Database Isolation

### Decision: Использовать тестовую БД + TRUNCATE между тестами

**Rationale**: Изоляция тестов важна для детерминированности. Тестовая БД уже настроена в проекте.

### Паттерн

```python
from app.database import async_session
from sqlalchemy import text

@pytest.fixture
async def db_session():
    """Provide clean database session for each test."""
    async with async_session() as session:
        # Clean tables before test
        await session.execute(text("TRUNCATE users, user_roles, guest_profiles, business_profiles CASCADE"))
        await session.commit()
        yield session

@pytest.fixture
async def test_roles(db_session):
    """Create standard roles for testing."""
    from app.models import Role
    roles = [
        Role(code="organizer", name="Организатор"),
        Role(code="student", name="Студент"),
        Role(code="expert", name="Эксперт"),
        Role(code="guest", name="Гость"),
        Role(code="business", name="Бизнес-партнёр"),
    ]
    for role in roles:
        db_session.add(role)
    await db_session.commit()
    return roles
```

---

## 5. LLM Mocking

### Decision: Mock `llm_client.send_chat_completion`

**Rationale**: LLM вызовы должны быть детерминированными и быстрыми в тестах.

### Паттерн

```python
from unittest.mock import AsyncMock, patch

@pytest.fixture
def mock_llm():
    """Mock LLM client with predefined responses."""
    async def fake_llm(system_prompt, user_prompt, json_mode=False):
        # Return predefined responses based on prompt content
        if "рекомендации" in user_prompt.lower():
            return {"projects": [{"id": "1", "score": 90}]}
        if "вопросы" in user_prompt.lower():
            return {"questions": ["Какую проблему решает проект?"]}
        return {}

    with patch("app.services.llm_client.send_chat_completion", side_effect=fake_llm) as mock:
        yield mock

@pytest.fixture
def mock_llm_unavailable():
    """Mock LLM client to simulate unavailability."""
    with patch("app.services.llm_client.send_chat_completion", side_effect=Exception("LLM unavailable")) as mock:
        yield mock
```

---

## 6. Test Structure

### Decision: Отдельный модуль `tests/test_handlers/`

**Rationale**: Группировка smoke-тестов хендлеров отдельно от unit/integration тестов.

### Структура файлов

```
backend/tests/
├── conftest.py              # Shared fixtures (db, app)
├── test_handlers/
│   ├── __init__.py
│   ├── conftest.py          # Handler-specific fixtures (mock_bot, make_update)
│   ├── test_onboarding.py   # 3 tests
│   ├── test_guest_profiling.py    # 3 tests
│   ├── test_business_profiling.py # 3 tests
│   ├── test_recommendations.py    # 3 tests
│   └── test_qa_helper.py          # 3 tests
```

### Запуск тестов

```bash
# Все smoke-тесты хендлеров
pytest tests/test_handlers/ -v

# Конкретный flow
pytest tests/test_handlers/test_onboarding.py -v

# С измерением времени
pytest tests/test_handlers/ -v --durations=0
```

---

## Summary

| Aspect | Decision |
|--------|----------|
| Update creation | `Update.de_json()` from dict |
| Bot mocking | `patch` on `Bot.send_message`, etc. |
| Async testing | `pytest-asyncio` + `app.process_update()` |
| DB isolation | TRUNCATE between tests |
| LLM mocking | `patch` on `llm_client.send_chat_completion` |
| Test structure | `tests/test_handlers/*.py` |
