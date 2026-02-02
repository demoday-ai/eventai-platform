# Quickstart: Профилирование и программа для гостей (EPIC-005)

**Date**: 2026-02-02
**Branch**: `005-guest-profiling`

## Integration Scenarios

### Сценарий 1: Гость проходит профилирование через бота

```
1. Гость нажимает /start → выбирает "Гость" → "AI-практик"
2. Бот автоматически: "Укажите интересы для персональной программы" + кнопка "Начать"
3. Гость нажимает "Начать"
4. Бот показывает inline-кнопки с тегами (top-15 по количеству проектов):
   [NLP] [CV] [Agents] [EdTech] [FinTech] [Security] ...
   Нажатые кнопки toggle: [✓ NLP] [CV] [✓ FinTech] ...
5. Гость выбирает NLP и FinTech кнопками
6. Гость пишет: "Интересует антифрод и hiring automation"
7. Гость нажимает "Готово"
8. AI извлекает из текста: tags=["FinTech"], keywords=["антифрод", "hiring automation"]
9. Бот: "Вас интересует: NLP, FinTech, антифрод, hiring automation. Верно?"
   [Да] [Нет, изменить]
10. Гость нажимает "Да"
11. Профиль сохранён. Бот: "Профиль сохранён! Сгенерировать программу?" [Да]
12. Гость нажимает "Да"
13. Система генерирует подборку (≤10 секунд):
    a. IDF tag overlap: score 330 проектов по NLP + FinTech
    b. LLM re-ranking: top-20 → top-15 с учётом "антифрод"
    c. LLM summaries: 2-3 предложения для каждого из 15 проектов
14. Бот отправляет:
    "🎯 Обязательно посетить:
    1. AI AntifraudX — NLP-модель для антифрод анализа...
       Зал 3 · NLP, FinTech · @author1
    2. ...

    ⏰ Если останется время:
    6. ...
    "
    [Подробнее: 1] [Подробнее: 2] ... [Обновить профиль]
```

### Сценарий 2: Гость запрашивает детали проекта

```
1. Гость нажимает "Подробнее: 3"
2. Бот показывает:
   "📋 AI RecruitBot
   Автоматизация рекрутинга с помощью NLP...
   [полное описание]

   Теги: NLP, HR, Automation
   Автор: Иван Иванов
   Зал: 2
   Telegram: @ivanivanov
   Релевантность: 87%"
   [Назад к программе]
```

### Сценарий 3: Обновление профиля

```
1. Гость вводит /profile
2. Бот: "Ваш текущий профиль: NLP, FinTech, антифрод. Обновить?"
   [Да, обновить] [Нет]
3. Гость нажимает "Да"
4. → Возвращается к шагу 4 из сценария 1 с предыдущими тегами выбранными
```

### Сценарий 4: LLM недоступен (graceful degradation)

```
1. Гость выбирает теги кнопками + пишет текст
2. AI extraction fails → бот: "Текст не удалось обработать, используем выбранные тематики."
3. Профиль сохранён только с selected_tags (без extracted_tags/keywords)
4. Генерация подборки: только IDF tag overlap (без LLM re-ranking)
5. Краткие описания: первые 2 предложения из оригинального description (без LLM summaries)
6. Гость всё равно получает подборку
```

### Сценарий 5: Мало подходящих проектов

```
1. Гость с профилем "BioTech" (только 3 проекта с этим тегом)
2. Система: 3 проекта по профилю + 7 популярных проектов (по общему рейтингу)
3. Бот: показывает подборку с пометкой для дополнительных: "По общей релевантности"
```

## Bot Command Summary

| Command | Role | Description |
|---------|------|-------------|
| /profile | Guest, Business | Начать/обновить профилирование |
| (auto) | Guest | Автоматически после онбординга |

## Conversation States

```
CHOOSE_TAGS → ENTER_TEXT → CONFIRM_PROFILE → GENERATE_PROGRAM → VIEW_PROGRAM → VIEW_DETAIL
                                    ↓ (Нет)
                               CHOOSE_TAGS (loop)
```

| State | Input | Next State |
|-------|-------|------------|
| CHOOSE_TAGS | Inline tag toggle + "Готово" | CONFIRM_PROFILE (если есть текст: через ENTER_TEXT) |
| CHOOSE_TAGS | Free text message | CONFIRM_PROFILE |
| ENTER_TEXT | Текст | CONFIRM_PROFILE |
| ENTER_TEXT | "Пропустить" | CONFIRM_PROFILE |
| CONFIRM_PROFILE | "Да" | GENERATE_PROGRAM |
| CONFIRM_PROFILE | "Нет, изменить" | CHOOSE_TAGS |
| GENERATE_PROGRAM | (auto) | VIEW_PROGRAM |
| VIEW_PROGRAM | "Подробнее: N" | VIEW_DETAIL |
| VIEW_PROGRAM | "Обновить профиль" | CHOOSE_TAGS |
| VIEW_DETAIL | "Назад" | VIEW_PROGRAM |

## LLM Prompts

### Text extraction prompt

```
System: Ты AI-ассистент для Demo Day. Проанализируй текст гостя и извлеки интересы.
Допустимые теги: {tag_list}
Верни JSON строго в формате:
{"tags": ["tag1", "tag2"], "keywords": ["keyword1", "keyword2"]}
tags — из списка допустимых. keywords — дополнительные ключевые слова не из списка.

User: {guest_raw_text}
```

### Re-ranking prompt

```
System: Ты AI-ассистент для Demo Day. Перед тобой профиль гостя и 20 проектов-кандидатов.
Отранжируй top-15 по релевантности к профилю гостя. Учитывай не только теги, но и ключевые слова из свободного текста.
Верни JSON строго в формате:
{"ranked": [{"project_id": "...", "score": 0.95}, ...]}

User: Профиль: теги={tags}, ключевые слова={keywords}, текст="{raw_text}"
Проекты: {projects_json}
```

### Summary generation prompt

```
System: Ты AI-ассистент для Demo Day. Сгенерируй краткое описание (2-3 предложения) каждого проекта, адаптированное под интересы гостя. Подчеркни аспекты релевантные для гостя.
Верни JSON строго в формате:
{"summaries": [{"project_id": "...", "summary": "..."}, ...]}

User: Профиль гостя: {guest_interests}
Проекты:
{projects_with_descriptions}
```
