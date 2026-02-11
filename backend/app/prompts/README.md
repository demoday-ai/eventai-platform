# LLM Prompts

Централизованное хранилище всех LLM-промптов для проекта EventAI.

## Структура

```
app/prompts/
├── bot/                    # Промпты для Telegram-бота
│   ├── agent.py           # Агент-режим (VIEW_PROGRAM state)
│   └── __init__.py
├── guest/                  # Промпты для гостей
│   ├── profiling.py       # Профилирование гостей
│   ├── qa.py              # Q&A-помощь и сравнение проектов
│   └── __init__.py
├── admin/                  # Промпты для админ-функций
│   ├── clustering.py      # Кластеризация проектов по залам
│   ├── tags.py            # Генерация тегов
│   └── __init__.py
├── __init__.py
└── README.md
```

## Принципы

### 1. Версионирование
Каждый файл промптов имеет версию и дату последнего обновления:

```python
"""Prompts for guest profiling.

Version: 1.0.0
Last updated: 2026-02-11
"""
```

### 2. Разделение статических и динамических промптов

**Статические промпты** (константы):
```python
TEXT_EXTRACTION_SYSTEM = """Ты AI-ассистент для Demo Day.
Проанализируй текст гостя и извлеки интересы..."""
```

**Динамические промпты** (функции):
```python
def build_agent_system_prompt(
    is_business: bool,
    profile_info: str,
    ...
) -> str:
    """Build system prompt for agent mode."""
    return f"Ты — AI-куратор...\n{profile_info}..."
```

### 3. Документация
Все функции имеют docstrings с:
- Описанием назначения
- Параметрами (Args)
- Возвращаемым значением (Returns)
- Примерами использования (Example)

### 4. Именование
- Константы: `UPPERCASE_WITH_UNDERSCORES`
- Функции: `build_*_prompt()` или `get_*_prompt()`
- System prompts: заканчиваются на `_SYSTEM`

## Миграция сервисов

### Статус миграции

| Сервис | Промпты | Статус |
|--------|---------|--------|
| `profiling_service.py` | `prompts/guest/profiling.py` | ⏳ TODO |
| `qa_service.py` | `prompts/guest/qa.py` | ⏳ TODO |
| `clustering_service.py` | `prompts/admin/clustering.py` | ⏳ TODO |
| `tag_service.py` | `prompts/admin/tags.py` | ⏳ TODO |
| `start.py` (bot handler) | `prompts/bot/agent.py` | ⏳ TODO |

### Как мигрировать сервис

**Шаг 1:** Добавить импорты

```python
# Old (промпты в файле)
TEXT_EXTRACTION_SYSTEM = """..."""

# New (импорт из prompts)
from app.prompts.guest.profiling import TEXT_EXTRACTION_SYSTEM
```

**Шаг 2:** Заменить вызовы функций

```python
# Old
system_prompt = _get_profile_agent_system()

# New
from app.prompts.guest.profiling import get_profile_agent_system
system_prompt = get_profile_agent_system(tag_list)
```

**Шаг 3:** Удалить старые промпты из файла

```python
# Удалить:
# TEXT_EXTRACTION_SYSTEM = """..."""
# def _get_profile_agent_system(): ...
```

**Шаг 4:** Запустить тесты

```bash
cd backend
.venv/bin/python -m pytest tests/ --ignore=tests/e2e -v
```

## A/B тестирование промптов

Промпты можно версионировать для A/B тестов:

```python
# prompts/guest/profiling.py
PROFILE_AGENT_VARIANTS = {
    "v1_strict": get_profile_agent_system,  # Current (strict 2 messages)
    "v2_flexible": get_profile_agent_system_v2,  # Flexible message count
}

# В сервисе:
variant = "v1_strict"  # or from config/feature flag
prompt_fn = PROFILE_AGENT_VARIANTS[variant]
system_prompt = prompt_fn(tag_list)
```

## Best Practices

1. **Не дублируй промпты** — один source of truth в `app/prompts/`
2. **Версионируй изменения** — обновляй VERSION при изменении промпта
3. **Добавляй few-shot примеры** — помогает LLM понять формат ответа
4. **Валидируй JSON-ответы** — используй json_mode=True в llm_client
5. **Логируй промпты** — при дебаге полезно видеть что отправлялось в LLM

## Troubleshooting

**Q: Промпт возвращает не тот формат JSON?**

A: Проверь что:
1. `json_mode=True` в `llm_client.send_chat_completion()`
2. В промпте явно указан формат: `Верни JSON строго в формате: {...}`
3. Есть few-shot примеры правильного ответа

**Q: Как добавить новый промпт?**

A:
1. Определи категорию (bot/guest/admin)
2. Создай файл или добавь в существующий
3. Документируй (docstring + VERSION)
4. Используй в сервисе через импорт
5. Добавь тесты на промпт (валидация формата)

**Q: Промпт слишком длинный (>8000 токенов)?**

A:
1. Убери лишние few-shot примеры (оставь 2-3 лучших)
2. Сократи описания в ROLE_CONTEXTS
3. Используй summarization для длинных данных (descriptions проектов)
4. Рассмотри prompt compression (LLMLingua)
