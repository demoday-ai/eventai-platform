# Data Model: Test Fixtures

**Feature**: 016-handler-smoke-tests
**Date**: 2026-02-03

---

## Test Entities

### TestUser

Эмулированный пользователь Telegram для тестов.

| Field | Type | Description |
|-------|------|-------------|
| telegram_user_id | int | Уникальный ID пользователя (123, 456, ...) |
| username | str | Username (@test_user) |
| first_name | str | Имя пользователя |
| role | str | Роль: organizer, student, expert, guest, business |

### MockUpdate Factory

Фабрика для создания Telegram Update объектов.

```python
# Message update
make_message_update(
    user_id: int,
    chat_id: int,
    text: str,
    update_id: int = 1,
) -> dict

# Callback query update
make_callback_update(
    user_id: int,
    chat_id: int,
    callback_data: str,
    update_id: int = 1,
) -> dict
```

---

## Test Fixtures

### Database Fixtures

| Fixture | Scope | Description |
|---------|-------|-------------|
| `db_session` | function | Чистая сессия БД (TRUNCATE перед каждым тестом) |
| `test_roles` | function | 5 стандартных ролей в БД |
| `test_event` | function | Тестовое событие (Demo Day) |
| `test_projects` | function | 5 тестовых проектов с тегами |
| `test_tags` | function | Стандартные теги (NLP, CV, LLM, ...) |

### Bot Fixtures

| Fixture | Scope | Description |
|---------|-------|-------------|
| `app` | function | Инициализированное Application с хендлерами |
| `mock_bot_methods` | function | Mock для send_message, edit_message_text, answer_callback_query |
| `mock_llm` | function | Mock LLM с предопределёнными ответами |
| `mock_llm_unavailable` | function | Mock LLM, который выбрасывает исключение |

### Helper Fixtures

| Fixture | Scope | Description |
|---------|-------|-------------|
| `make_message_update` | session | Фабрика для message updates |
| `make_callback_update` | session | Фабрика для callback updates |
| `registered_guest` | function | Пользователь с ролью guest в БД |
| `registered_business` | function | Пользователь с ролью business в БД |
| `guest_with_profile` | function | Гость с заполненным GuestProfile |
| `business_with_profile` | function | Бизнес с заполненным BusinessProfile |

---

## Predefined Test Data

### LLM Mock Responses

```python
MOCK_RECOMMENDATIONS = {
    "must_visit": [
        {"id": "proj-1", "title": "AI Project 1", "score": 90},
        {"id": "proj-2", "title": "AI Project 2", "score": 85},
    ],
    "if_time": [
        {"id": "proj-3", "title": "AI Project 3", "score": 70},
    ],
    "total": 3,
}

MOCK_QA_QUESTIONS = {
    "questions": [
        "Какую проблему решает ваш проект?",
        "Какие технологии используете?",
        "Каковы планы развития?",
    ]
}

MOCK_CLUSTERING = {
    "rooms": [
        {"name": "NLP и языковые модели", "project_ids": ["p1", "p2"]},
        {"name": "Computer Vision", "project_ids": ["p3", "p4"]},
    ]
}
```

### Test Users

```python
TEST_USERS = {
    "new_user": {"id": 100, "username": "new_user", "first_name": "Новый"},
    "guest": {"id": 200, "username": "guest_user", "first_name": "Гость"},
    "business": {"id": 300, "username": "biz_user", "first_name": "Партнёр"},
    "organizer": {"id": 400, "username": "org_user", "first_name": "Орг"},
}
```

---

## State Transitions (for testing)

### Onboarding Flow

```
[New User] --/start--> [Role Selection] --role:guest--> [Registered Guest]
                                        --role:business--> [Registered Business]
                                        --role:*--> [Registered User]
```

### Guest Profiling Flow

```
[Registered Guest] --prof:start--> [Tag Selection] --prof:tags--> [Keywords Input]
                                                   --prof:confirm--> [Profile Saved]
                                                   --prof:edit--> [Tag Selection]
```

### Business Profiling Flow

```
[Registered Business] --bp:start--> [Objective Selection] --bp:obj--> [Industry Selection]
                                                          --bp:ind--> [Tech Selection]
                                                          --bp:confirm--> [Profile Saved]
```
