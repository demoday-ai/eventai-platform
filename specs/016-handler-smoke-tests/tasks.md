# Tasks: Smoke-тесты на критичные хендлеры

**Input**: Design documents from `/specs/016-handler-smoke-tests/`
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓

**Target**: 15 тестов (3 сценария × 5 flows), выполнение ≤60 секунд

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1-US5)

---

## Phase 1: Setup (Test Infrastructure)

**Purpose**: Создание базовой структуры тестов и fixtures

- [x] T001 Create test directory structure `backend/tests/test_handlers/`
- [x] T002 Create `backend/tests/test_handlers/__init__.py`
- [x] T003 Create shared fixtures in `backend/tests/test_handlers/conftest.py`

---

## Phase 2: Foundational (Mock Factories)

**Purpose**: Создание mock factories и базовых fixtures для всех тестов

**⚠️ CRITICAL**: Все User Story зависят от этих fixtures

**Note**: Изменён подход — вместо real DB и PTB Application используем direct handler testing с MagicMock/AsyncMock. Это упростило тесты и устранило проблемы с PTB 21.x immutable objects и PostgreSQL-specific types в SQLite.

- [x] T004 [P] Implement `make_message_update()` factory in conftest.py (simplified to MagicMock in tests)
- [x] T005 [P] Implement `make_callback_update()` factory in conftest.py (simplified to MagicMock in tests)
- [x] T006 ~~Implement `app` fixture~~ (not needed - direct handler testing)
- [x] T007 [P] Implement `mock_bot_methods` fixture (send_message, edit_message_text, answer_callback_query)
- [x] T008 [P] ~~Implement `db_session` fixture~~ (not needed - service layer mocking)
- [x] T009 [P] ~~Implement `test_roles` fixture~~ (inline MagicMock fixtures per test file)
- [x] T010 [P] ~~Implement `mock_llm` fixture~~ (service layer mocking instead)
- [x] T011 [P] ~~Implement `mock_llm_unavailable` fixture~~ (service layer mocking instead)

**Checkpoint**: Test infrastructure ready - can implement smoke tests

---

## Phase 3: User Story 1 - Онбординг (Priority: P1) 🎯 MVP

**Goal**: Smoke-тесты для flow онбординга (/start, выбор роли)

**Independent Test**: `pytest tests/test_handlers/test_onboarding.py -v`

### Implementation

- [x] T012 [US1] Create `backend/tests/test_handlers/test_onboarding.py`
- [x] T013 [US1] Test: `/start` для нового пользователя → приветствие + выбор роли
- [x] T014 [US1] Test: `/start` для существующего пользователя → корректная обработка повторной регистрации
- [x] T015 [US1] Test: Invalid callback (неизвестная роль) → graceful error handling

**Checkpoint**: ✅ Онбординг flow покрыт тестами (3 теста)

---

## Phase 4: User Story 2 - Профилирование гостя (Priority: P1)

**Goal**: Smoke-тесты для flow профилирования гостя

**Independent Test**: `pytest tests/test_handlers/test_guest_profiling.py -v`

### Prerequisites

- [x] T016 [US2] ~~Implement `registered_guest` fixture~~ (inline MagicMock)
- [x] T017 [P] [US2] ~~Implement `guest_with_profile` fixture~~ (inline MagicMock)
- [x] T018 [P] [US2] Implement `test_tags` fixture (теги NLP, CV, LLM и др.)

### Implementation

- [x] T019 [US2] Create `backend/tests/test_handlers/test_guest_profiling.py`
- [x] T020 [US2] Test: Полный flow профилирования (выбор тегов → ввод интересов → подтверждение)
- [x] T021 [US2] Test: Редактирование существующего профиля
- [x] T022 [US2] Test: Валидация (попытка подтвердить без выбора тегов)

**Checkpoint**: ✅ Guest profiling flow покрыт тестами (3 теста)

---

## Phase 5: User Story 3 - Профилирование бизнеса (Priority: P1)

**Goal**: Smoke-тесты для flow профилирования бизнес-партнёра

**Independent Test**: `pytest tests/test_handlers/test_business_profiling.py -v`

### Prerequisites

- [x] T023 [US3] ~~Implement `registered_business` fixture~~ (inline MagicMock)
- [x] T024 [P] [US3] ~~Implement `business_with_profile` fixture~~ (inline MagicMock)

### Implementation

- [x] T025 [US3] Create `backend/tests/test_handlers/test_business_profiling.py`
- [x] T026 [US3] Test: Полный flow (цель → отрасли → технологии → подтверждение)
- [x] T027 [US3] Test: Выбор objective = INVESTMENT → проверка сохранения
- [x] T028 [US3] Test: Обновление существующего профиля

**Checkpoint**: ✅ Business profiling flow покрыт тестами (3 теста)

---

## Phase 6: User Story 4 - Рекомендации (Priority: P2)

**Goal**: Smoke-тесты для генерации рекомендаций

**Independent Test**: `pytest tests/test_handlers/test_recommendations.py -v`

### Prerequisites

- [x] T029 [US4] ~~Implement `test_projects` fixture~~ (inline MagicMock)
- [x] T030 [P] [US4] Implement `test_event` fixture (Demo Day event) — inline MagicMock

### Implementation

- [x] T031 [US4] Create `backend/tests/test_handlers/test_recommendations.py`
- [x] T032 [US4] Test: Гость с профилем запрашивает рекомендации → непустой список
- [x] T033 [US4] Test: Бизнес-партнёр запрашивает рекомендации → соответствие целям
- [x] T034 [US4] Test: LLM недоступен → fallback поведение (mock_llm_unavailable)

**Checkpoint**: ✅ Recommendations flow покрыт тестами (3 теста)

---

## Phase 7: User Story 5 - Q&A Helper (Priority: P2)

**Goal**: Smoke-тесты для генерации Q&A вопросов

**Independent Test**: `pytest tests/test_handlers/test_qa_helper.py -v`

### Implementation

- [x] T035 [US5] Create `backend/tests/test_handlers/test_qa_helper.py`
- [x] T036 [US5] Test: Гость запрашивает вопросы для проекта → список вопросов
- [x] T037 [US5] Test: Бизнес (инвестор) запрашивает вопросы → тип BUSINESS_INVESTOR
- [x] T038 [US5] Test: LLM недоступен → fallback вопросы

**Checkpoint**: ✅ Q&A helper flow покрыт тестами (3 теста)

---

## Phase 8: Polish & Validation

**Purpose**: Финальная валидация и документация

- [x] T039 Run all tests: `pytest tests/test_handlers/ -v --durations=0` — ✅ 15 passed
- [x] T040 Verify execution time ≤60 seconds — ✅ 0.36s
- [x] T041 [P] Update quickstart.md с актуальными командами
- [x] T042 Commit and push to branch `016-handler-smoke-tests`

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1 (Setup) → Phase 2 (Foundational) → Phases 3-7 (User Stories) → Phase 8 (Polish)
```

### User Story Dependencies

- **US1 (Onboarding)**: Depends only on Phase 2 foundations
- **US2 (Guest Profiling)**: Depends on Phase 2 + `test_tags` fixture
- **US3 (Business Profiling)**: Depends on Phase 2, can run parallel with US2
- **US4 (Recommendations)**: Depends on US2/US3 fixtures (guest_with_profile, business_with_profile, test_projects)
- **US5 (Q&A Helper)**: Depends on US4 fixtures (reuses test_projects, profiles)

### Parallel Opportunities

```bash
# Phase 2 - все fixtures можно создавать параллельно:
T004, T005, T007, T008, T009, T010, T011

# US2/US3 prerequisites параллельно:
T017, T018 (US2) || T024 (US3)

# US4 prerequisites параллельно:
T029, T030
```

---

## Test Count Summary

| Phase | User Story | Tests |
|-------|-----------|-------|
| 3 | US1: Онбординг | 3 |
| 4 | US2: Guest Profiling | 3 |
| 5 | US3: Business Profiling | 3 |
| 6 | US4: Recommendations | 3 |
| 7 | US5: Q&A Helper | 3 |
| **Total** | | **15** |

---

## Implementation Strategy

### MVP First (P1 Only)

1. Phase 1-2: Setup + Foundational
2. Phase 3: US1 Onboarding (3 tests)
3. Phase 4: US2 Guest Profiling (3 tests)
4. Phase 5: US3 Business Profiling (3 tests)
5. **STOP**: 9 тестов покрывают критичные P1 flows

### Full Implementation

1. Complete MVP (9 tests)
2. Phase 6: US4 Recommendations (3 tests)
3. Phase 7: US5 Q&A Helper (3 tests)
4. Phase 8: Polish
5. **Result**: 15 tests, все flows покрыты

---

## Notes

- Все тесты используют `Update.de_json()` для создания mock Update
- LLM mock'ается через `patch("app.services.llm_client.send_chat_completion")`
- БД очищается TRUNCATE между тестами для изоляции
- Каждый тест-файл можно запускать независимо
