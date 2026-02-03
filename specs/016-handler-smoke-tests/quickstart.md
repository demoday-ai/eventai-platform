# Quickstart: Running Handler Smoke Tests

**Feature**: 016-handler-smoke-tests
**Date**: 2026-02-03
**Status**: ✅ Implemented (15 tests passing)

---

## Prerequisites

- Python 3.12+ установлен
- Проект клонирован: `demoday-core/`
- Зависимости установлены: `pip install -r requirements.txt`

**Важно**: Тесты НЕ требуют:
- Реальный BOT_TOKEN (используют mocks)
- Работающую БД (используют MagicMock)
- LLM API ключи (сервисы mock'аются)

## Quick Run

```bash
# Из директории backend/
cd backend

# Запуск всех smoke-тестов хендлеров
pytest tests/test_handlers/ -v

# Или с подробностями по времени
pytest tests/test_handlers/ -v --durations=0
```

## Run Specific Test Module

```bash
# Только онбординг (US1)
pytest tests/test_handlers/test_onboarding.py -v

# Только профилирование гостя (US2)
pytest tests/test_handlers/test_guest_profiling.py -v

# Только профилирование бизнеса (US3)
pytest tests/test_handlers/test_business_profiling.py -v

# Только рекомендации (US4)
pytest tests/test_handlers/test_recommendations.py -v

# Только Q&A helper (US5)
pytest tests/test_handlers/test_qa_helper.py -v
```

## Run with Timing

```bash
# Показать время каждого теста
pytest tests/test_handlers/ -v --durations=0

# Проверить что все тесты укладываются в 60 секунд
pytest tests/test_handlers/ -v --timeout=60
```

## Expected Output

```
tests/test_handlers/test_business_profiling.py::test_business_profiling_flow PASSED
tests/test_handlers/test_business_profiling.py::test_objective_investment_saved PASSED
tests/test_handlers/test_business_profiling.py::test_update_existing_business_profile PASSED
tests/test_handlers/test_guest_profiling.py::test_profiling_flow_complete PASSED
tests/test_handlers/test_guest_profiling.py::test_edit_existing_profile PASSED
tests/test_handlers/test_guest_profiling.py::test_validation_min_tags PASSED
tests/test_handlers/test_onboarding.py::test_start_command_new_user PASSED
tests/test_handlers/test_onboarding.py::test_start_command_existing_user PASSED
tests/test_handlers/test_onboarding.py::test_invalid_role_callback PASSED
tests/test_handlers/test_qa_helper.py::test_guest_qa_questions PASSED
tests/test_handlers/test_qa_helper.py::test_business_investor_qa_questions PASSED
tests/test_handlers/test_qa_helper.py::test_qa_llm_fallback PASSED
tests/test_handlers/test_recommendations.py::test_guest_recommendations PASSED
tests/test_handlers/test_recommendations.py::test_business_recommendations PASSED
tests/test_handlers/test_recommendations.py::test_recommendations_llm_fallback PASSED

============================= 15 passed in 0.36s ==============================
```

## Troubleshooting

### Import errors

```bash
# Убедитесь что PYTHONPATH включает backend/
cd backend
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
pytest tests/test_handlers/ -v
```

### Missing dependencies

```bash
# Установите тестовые зависимости
pip install pytest pytest-asyncio
```

## CI Integration

```yaml
# .github/workflows/test.yml
- name: Run handler smoke tests
  run: |
    cd backend
    pytest tests/test_handlers/ -v --timeout=60
```

## Test Coverage

| Module | Tests | Description |
|--------|-------|-------------|
| test_onboarding.py | 3 | /start, повторная регистрация, invalid callback |
| test_guest_profiling.py | 3 | flow, edit, validation |
| test_business_profiling.py | 3 | flow, objective, update |
| test_recommendations.py | 3 | guest, business, LLM fallback |
| test_qa_helper.py | 3 | guest, business, LLM fallback |
| **Total** | **15** | |
