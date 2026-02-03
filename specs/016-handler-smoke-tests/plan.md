# Implementation Plan: Smoke-тесты на критичные хендлеры

**Branch**: `016-handler-smoke-tests` | **Date**: 2026-02-03 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/016-handler-smoke-tests/spec.md`

## Summary

Создание smoke-тестов для 5 критичных flows Telegram-бота: онбординг, профилирование гостя, профилирование бизнеса, рекомендации, Q&A helper. Тесты используют mock для Telegram API и LLM, изолированную тестовую БД. Минимум 15 тестов (3 сценария × 5 flows), выполнение за ≤60 секунд.

## Technical Context

**Language/Version**: Python 3.12+
**Primary Dependencies**: pytest, pytest-asyncio, python-telegram-bot 21.x, SQLAlchemy 2.0 (async)
**Storage**: PostgreSQL 16 (тестовая БД)
**Testing**: pytest + pytest-asyncio
**Target Platform**: Linux server (Docker)
**Project Type**: Backend (существующий проект)
**Performance Goals**: Все тесты выполняются за ≤60 секунд
**Constraints**: Не требует реального Bot Token / LLM API ключа
**Scale/Scope**: 15+ тест-кейсов, 5 хендлер-модулей

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Telegram-First | ✅ PASS | Тесты покрывают Telegram Bot handlers |
| II. AI-Augmented, Human-Approved | ✅ PASS | LLM mock'ается, graceful degradation тестируется |
| III. Data-Driven | ✅ PASS | Тестовые данные изолированы |
| IV. Pragmatic Development | ✅ PASS | Smoke-тесты — минимальный набор для стабильности к DD |

**Coding Standards Compliance:**
- pytest — стандартный фреймворк (уже используется)
- Тесты покрывают критичные пути (онбординг, профилирование, рекомендации)

## Project Structure

### Documentation (this feature)

```text
specs/016-handler-smoke-tests/
├── plan.md              # This file
├── research.md          # Phase 0: mocking strategies
├── data-model.md        # Phase 1: test fixtures
├── quickstart.md        # Phase 1: how to run tests
├── contracts/           # N/A (no API contracts for tests)
└── tasks.md             # Phase 2 output
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── bot/
│   │   └── handlers/        # Тестируемые хендлеры
│   │       ├── onboarding.py
│   │       ├── guest_profiling.py
│   │       ├── business_profiling.py
│   │       └── ...
│   ├── services/            # Сервисы (profiling, recommendations, qa)
│   └── models/              # SQLAlchemy models
│
└── tests/
    ├── conftest.py          # Fixtures: db, mock_bot, mock_update
    ├── test_handlers/       # NEW: Smoke tests
    │   ├── __init__.py
    │   ├── conftest.py      # Handler-specific fixtures
    │   ├── test_onboarding.py
    │   ├── test_guest_profiling.py
    │   ├── test_business_profiling.py
    │   ├── test_recommendations.py
    │   └── test_qa_helper.py
    └── ...
```

**Structure Decision**: Тесты размещаются в `backend/tests/test_handlers/` — отдельная директория для smoke-тестов хендлеров. Используется существующая структура `backend/tests/`.

## Complexity Tracking

> No violations detected. Feature aligns with Constitution principles.

---

## Phase 0: Research

### Research Tasks

1. **Mocking python-telegram-bot 21.x**: Как создавать mock Update, CallbackQuery, Context
2. **Async test patterns**: pytest-asyncio + SQLAlchemy async session в тестах
3. **LLM mocking**: Как подменять llm_client для детерминированных тестов

### Findings

See [research.md](./research.md) for detailed findings.
