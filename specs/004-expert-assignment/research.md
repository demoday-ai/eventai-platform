# Research: Распределение экспертов (EPIC-004)

**Date**: 2026-02-02 | **Status**: Complete

## R1: Matching Algorithm — Tag Overlap vs LLM-based

**Decision**: Weighted tag-overlap (алгоритмический) с LLM fallback для смежных тегов.

**Rationale**: 294 эксперта × 10 комнат — слишком мало данных, чтобы оправдать вызов LLM на каждое сопоставление. Tag-overlap работает детерминировано, предсказуемо и мгновенно. LLM используется только для определения смежности тегов (однократный вызов при запуске матчинга — 31 тег → матрица смежности).

**Alternatives considered**:
- **Полный LLM-матчинг** (передать всех экспертов + все комнаты в один промпт): Rejected — 294 эксперта не поместятся в один промпт; результат не детерминирован; нельзя объяснить "почему этот эксперт здесь". Дорого при повторных запусках.
- **Embedding similarity** (эмбеддинги тегов, cosine similarity): Rejected — избыточно для 31 дискретного тега. Эмбеддинги полезны при свободнотекстовых описаниях, не при фиксированной таксономии. Добавляет зависимость (модель эмбеддингов).
- **Ручное определение смежности** (hardcoded adjacency matrix): Rejected — не масштабируется при изменении набора тегов; требует ручного труда организатора.

## R2: Tag Weighting Strategy

**Decision**: Inverse frequency weighting (IDF-подобный). Вес тега = `log(N / count(tag))`, где N = общее число экспертов, count(tag) = число экспертов с этим тегом.

**Rationale**: Из реальных данных — "LLM" тег у 29 из 294 экспертов (10%), "Security" — у 2 (0.7%). Эксперт с Security ценнее для Security-комнаты, чем эксперт с LLM для LLM-комнаты. IDF автоматически учитывает это без ручной настройки.

**Formula**: Для каждого эксперта E и комнаты R:
```
score(E, R) = sum(
    idf(tag) * match(tag, R)
    for tag in E.tags
)
where:
    idf(tag) = log(total_experts / experts_with_tag)
    match(tag, R) = 1.0 if tag in R.tags
                    0.5 if tag in R.adjacent_tags
                    0.0 otherwise
```

Эксперт назначается в комнату с наивысшим score. При равенстве — в комнату с меньшим покрытием.

**Alternatives considered**:
- **Равные веса** (1.0 за каждое совпадение): Rejected — эксперт с 10 тегами (все популярные) набирает high score везде, но реально не является узким специалистом.
- **Ручные приоритеты от экспертов**: Rejected для MVP — требует дополнительного онбординга. Может быть добавлено в P2.
- **TF-IDF по описанию**: Rejected — у нас дискретные теги, не текст.

## R3: Adjacent Tag Resolution via LLM

**Decision**: Однократный LLM-вызов при запуске матчинга. Передаём список всех 31 тегов, просим вернуть JSON с adjacency pairs.

**Rationale**: Вызов LLM один раз (не на каждого эксперта). Результат кешируется в памяти до следующего матчинга. Промпт конкретный, результат валидируется (только теги из списка).

**LLM Prompt Template**:
```
Дан список тегов AI/ML проектов: [tag1, tag2, ..., tag31].
Определи семантически близкие пары тегов в контексте Demo Day AI-проектов.
Близкие = эксперт с одним тегом может квалифицированно оценить проект с другим.

Верни JSON: {"adjacency": [["tag_a", "tag_b"], ...]}
Только пары из данного списка. Максимум 2-3 смежных тега для каждого.
```

**Fallback**: Если LLM недоступен — матчинг работает только по точным совпадениям (graceful degradation per Constitution II).

**Alternatives considered**:
- **Hardcoded adjacency**: Rejected — требует ручного труда, не адаптируется при изменении тегов.
- **LLM per expert**: Rejected — 294 вызова вместо 1, дорого и медленно.
- **Embedding cosine**: Rejected — те же причины что R1.

## R4: Seed Data Preparation

**Decision**: Merge `data/expert-mapping.json` (294 записи: id, name, telegram) + `data/experts-public.json` (294 записи: id, expertise_tags, dd_status, position) по общему полю `id` → `data/seed/experts_seed.json`.

**Rationale**: Две таблицы хранят разные аспекты одного эксперта. Seed-файл объединяет их для загрузки в БД. Скрипт `scripts/prepare_expert_seed.py` делает merge (аналогично `scripts/prepare_seed.py` для EPIC-002).

**Output format**:
```json
[{
  "id": "EXP-001",
  "name": "Абодо Элунду Брис Дональд",
  "telegram": "@repeat_afterme_15",
  "position": "ALUMNI25",
  "expertise_tags": [],
  "dd_status": "Не указан",
  "inviter": "Катя"
}]
```

**Experts without tags**: 86 из 294 (29%) не имеют тегов. Они не участвуют в автоматическом матчинге → попадают в список "без тегов" для организатора.

**Alternatives considered**:
- **Загружать из двух файлов отдельно**: Rejected — лишняя сложность, join в runtime.
- **Только expert-mapping.json**: Rejected — нет тегов, матчинг невозможен.

## R5: Invite Flow Architecture

**Decision**: Experts come to bot via shared link. Bot recognizes by Telegram username.

**Rationale**: Telegram Bot API не позволяет отправить сообщение пользователю, который не начал `/start`. Организатор делится ссылкой `t.me/botname?start=expert` в общем чате экспертов. При `/start` бот проверяет `update.effective_user.username` против seed-данных. Если найден → показывает персональное приглашение.

**Flow**:
1. Организатор утверждает распределение → видит превью (N экспертов, пример сообщения)
2. Организатор подтверждает → система сохраняет статус "invite_ready" для каждого assignment
3. Организатор получает ссылку `t.me/botname?start=expert` для чата экспертов
4. Эксперт нажимает ссылку → `/start expert` → бот ищет username в БД
5. Если найден: показывает приглашение с комнатой + кнопки ("Иду" / "Другая комната" / "Не смогу")
6. Если не найден: "Вы не в списке экспертов. Обратитесь к организатору."

**Reminders**: APScheduler (или asyncio-based scheduler) проверяет раз в день экспертов со статусом "invited" (пришли к боту, увидели приглашение, не ответили) > 3 дней → напоминание. Для не пришедших к боту — только через список организатору.

**Alternatives considered**:
- **Прямая рассылка через Bot API**: Impossible — бот не может писать первым. Только если эксперт ранее начал `/start` (из EPIC-001 онбординга), но не все эксперты онбордились.
- **Telegram Channel invite**: Rejected — каналы не поддерживают inline-кнопки, нет интерактива.
- **Email**: Rejected — Constitution I (Telegram-First).

## R6: Coverage Dashboard Format

**Decision**: Текстовое сообщение в Telegram с emoji-индикацией и пагинацией по комнатам.

**Rationale**: Telegram — единственный канал (Constitution I). Дашборд помещается в одно сообщение (< 4096 chars для 10 комнат). Формат:

```
📊 Покрытие экспертами (DD 2026-02-06)

🟢 Зал 1: NLP/LLM — 3/2 подтв. | 1 отказ | 2 нет ответа
🟢 Зал 2: CV/GAN — 2/2 подтв. | 0 отказ | 1 нет ответа
🟡 Зал 3: Agents — 1/2 подтв. | 1 отказ | 3 нет ответа
🔴 Зал 4: FinTech — 0/2 подтв. | 2 отказ | 1 нет ответа

Итого: 6/20 подтв. (30%) | 4 отказа | 7 нет ответа
```

Каждая комната — кнопка для drill-down (список экспертов, статусы).

**Alternatives considered**:
- **Веб-дашборд**: Rejected for MVP — Constitution I, лишний фронтенд.
- **Отдельные сообщения на комнату**: Rejected — 10 сообщений спамят, нет overview.

## R7: Scheduler for Reminders/Escalation

**Decision**: APScheduler (AsyncIOScheduler) с IntervalTrigger, проверка раз в 12 часов.

**Rationale**: Напоминания (3 дня) и эскалация (5 дней / за 2 дня до DD) — не real-time. Проверка 2 раза в сутки достаточна. APScheduler — легковесный, уже хорошо интегрируется с asyncio/FastAPI lifecycle.

**Alternative**: Celery — rejected (overkill для 2 периодических задач, добавляет Redis dependency).
**Alternative**: asyncio.sleep loop — rejected (хрупкий, нет retry, нет persistence).

## R8: Reuse of EPIC-002 Tags

**Decision**: Переиспользовать существующую таблицу `tags` из EPIC-002. Связать экспертов с тегами через `expert_tags` (аналогично `project_tags`).

**Rationale**: Теги едины для всей системы. Эксперт с тегом "NLP" должен матчиться с комнатой, содержащей NLP-проекты. Использование одной таблицы `tags` обеспечивает консистентность. Нет дублирования.

**Room tags derivation**: Теги комнаты = union тегов всех проектов в комнате (через `room_projects` → `projects` → `project_tags` → `tags`). Не хранятся отдельно — вычисляются на лету.

**Alternatives considered**:
- **Отдельная таблица expert_tags_dict**: Rejected — дублирование, рассинхронизация.
- **Свободнотекстовые теги**: Rejected — нужен точный match.
