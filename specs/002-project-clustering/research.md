# Research: Загрузка и AI-кластеризация проектов

**Branch**: `002-project-clustering` | **Date**: 2026-02-02

---

## R1: Подход к AI-кластеризации

### Decision
LLM-based кластеризация через OpenRouter API (GPT-4.1 / Claude). Один LLM-вызов получает все проекты (название + описание + теги), количество залов, и опциональный NL-фидбэк. Возвращает JSON с распределением проектов по залам + обоснование тематик.

### Rationale
- **Семантическое понимание**: LLM лучше классических методов (k-means на эмбеддингах) понимает тематическую близость "NLP + Agents" vs "CV + промышленность"
- **Обоснование**: LLM генерирует человекочитаемое обоснование тематики зала — FR-007
- **NL-фидбэк**: организатор может сказать "разделите NLP и агентов" — LLM это понимает нативно (FR-009)
- **Балансировка**: в system prompt задаём constraint "разница ≤5 проектов" — FR-005
- **Простота**: один API-вызов vs pipeline эмбеддинги → UMAP → HDBSCAN → постпроцессинг

### Alternatives Considered
1. **Embedding + k-means**: Хорош для масштаба (10k+ проектов), но для 305 проектов overkill. Не генерирует обоснования. Не поддерживает NL-фидбэк.
2. **Embedding + LLM labeling**: Двухэтапный: сначала кластеры embeddings, потом LLM именует. Сложнее, а NL-фидбэк всё равно требует LLM.
3. **Manual rules (теги → залы)**: Не работает когда у проекта 3 тега из разных тематик.

### Implementation Notes
- **Token budget**: 305 проектов × ~50 tokens (название + теги) = ~15k input tokens. С описаниями (~100 tokens) = ~30k. Укладывается в контекст GPT-4.1 (1M) и Claude (200k).
- **Chunking fallback**: если >500 проектов — разбить на батчи по 200, кластеризовать, merge.
- **Retry**: при LLM-ошибке — retry 3 раза с exponential backoff.
- **Validation**: после LLM-ответа проверить: каждый проект ровно в 1 зале, разница ≤5, JSON schema.

---

## R2: Формат LLM prompt для кластеризации

### Decision
Structured prompt с JSON output format:

```
System: Ты AI-ассистент для организации Demo Day. Распредели проекты по тематическим залам.
Constraints:
- Каждый проект ровно в одном зале
- Разница между самым большим и маленьким залом ≤ 5 проектов
- Группируй по тематической близости (NLP, CV, Agents, FinTech и т.д.)

User: Проекты (N штук, K залов):
[JSON array of {id, title, description, tags}]

{Фидбэк организатора (опционально): "..."}

Верни JSON:
{
  "rooms": [
    {
      "name": "Зал 1: NLP + Agents",
      "theme_rationale": "8 проектов связаны с обработкой языка...",
      "project_ids": ["uuid1", "uuid2", ...]
    }
  ]
}
```

### Rationale
- JSON output легко парсится и валидируется
- System prompt содержит constraints (балансировка, уникальность)
- NL-фидбэк добавляется в user message как дополнительная инструкция
- Названия залов генерируются LLM — информативны для организатора

---

## R3: Парсинг CSV/JSON файлов

### Decision
Парсинг в сервисном слое (project_service.py):
- **CSV**: `csv.DictReader`, ожидаемые колонки: `title`, `description`, `tags` (comma-separated), `author`, `telegram_contact`
- **JSON**: `json.loads`, ожидаемый формат: массив объектов с теми же полями
- Валидация через Pydantic schema (ProjectUploadRow)

### Rationale
- Стандартные библиотеки Python, без дополнительных зависимостей
- Pydantic валидация даёт чёткие сообщения об ошибках с номером строки
- Оба формата покрывают use case: CSV для Excel-пользователей, JSON для API

### Alternatives Considered
1. **pandas**: Overkill для парсинга, тяжёлая зависимость (~150MB).
2. **openpyxl (xlsx)**: Spec ограничивает CSV/JSON — xlsx вне скоупа.

---

## R4: Seed-данные из checkpoint-форм

### Decision
Одноразовый скрипт `scripts/prepare_seed.py` извлекает данные из `data/test/checkpoint12_anon.xlsx`:
- Листы: "1КР 13.10", "Научный трек", "Образовательный трек", "Индустриальный трек", "Стартап трек", "AI Product Альфа"
- Поля: col[6] "Название проекта" → title, col[12] "План работы" → description, col[13] "Ожидаемый результат" → description (concat), col[2] "ФИО" → author, col[3] "Телеграмм" → telegram_contact
- Теги: join по названию с `docs/00-research/past-demoday-projects.md` (парсинг markdown таблиц)
- Output: `data/seed/projects_seed.json`

### Rationale
- Предпарсенный JSON загружается мгновенно при первом запуске (seed_service.py)
- Не зависит от runtime-парсинга xlsx (openpyxl не нужен в production)
- Дедупликация по названию проекта при подготовке seed

---

## R5: Навигация wizard в боте

### Decision
ConversationHandler с состояниями:

```
UPLOAD → CONFIRM_REPLACE → CLUSTER_PARAMS → CLUSTERING → VIEW_RESULT → MOVE_PROJECT → APPROVE
```

Переходы:
1. `/projects` или кнопка "Проекты" → показать текущий статус (seed-данные или загруженные)
2. Загрузка файла → валидация → подтверждение замены (если данные уже есть) → CLUSTER_PARAMS
3. "Запустить кластеризацию" → параметры (K залов, default 6) → CLUSTERING (typing indicator)
4. Результат → VIEW_RESULT: навигация по залам, "Перенести проект", "Перегенерировать", "Утвердить"
5. "Утвердить" → APPROVE: подтверждение, фиксация

### Rationale
- Линейный flow минимизирует когнитивную нагрузку (Clarify Q3: wizard)
- ConversationHandler — тот же паттерн что в EPIC-001 (start.py)
- Кнопка "Назад" на каждом шаге (FR-014)

---

## R6: Отображение результатов кластеризации в Telegram

### Decision
Telegram ограничивает 4096 символов/сообщение. Для 305 проектов в 6 залах (~50 проектов/зал):
- **Обзор**: одно сообщение со списком залов (название + кол-во + первые 3 проекта) + inline-кнопки "Зал 1", "Зал 2", ...
- **Детали зала**: по нажатию кнопки — сообщение со списком проектов зала (название + теги). Если >4096 — пагинация.
- **Перенос**: кнопка "Перенести" у каждого проекта → выбор зала из inline-кнопок

### Rationale
- Укладывается в Telegram API limits
- Inline-кнопки — Constitution I (все действия через кнопки)
- Пагинация обеспечивает масштабируемость

---

## R7: OpenRouter API интеграция

### Decision
HTTP-клиент (httpx async) к OpenRouter API через Xray proxy кэмпа. Model: `openai/gpt-4.1` (primary), fallback `anthropic/claude-sonnet-4-20250514`.

### Rationale
- Constitution: OpenRouter API (GPT-4.1, Claude) через Xray proxy
- httpx уже в dev-зависимостях (для тестов), минимальная новая зависимость
- Async httpx совместим с FastAPI event loop
- Fallback на другую модель при ошибках основной

### Implementation Notes
- Base URL: через env var `OPENROUTER_BASE_URL` (Xray proxy)
- API key: через env var `OPENROUTER_API_KEY`
- Timeout: 120 sec (для кластеризации 305 проектов)
- Structured output: JSON mode / response_format
