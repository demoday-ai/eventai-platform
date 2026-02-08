# Data Model: Dashboard и прогресс

**Feature**: 019-admin-dashboard
**Date**: 2026-02-09

## Существующие сущности (без изменений)

### Event
| Field | Type | Notes |
|-------|------|-------|
| id | UUID | PK |
| name | str | Название мероприятия |
| start_date | date | Дата начала |
| end_date | date | Дата окончания |
| description | str? | Описание |

### Project
| Field | Type | Notes |
|-------|------|-------|
| id | UUID | PK |
| event_id | UUID | FK → Event |
| name | str | Название проекта |
| description | str? | |
| track | str? | Трек |

### ClusteringRun
| Field | Type | Notes |
|-------|------|-------|
| id | UUID | PK |
| event_id | UUID | FK → Event |
| status | str | draft / approved / superseded |
| approved_at | datetime? | Когда одобрена кластеризация |
| schedule_approved_at | datetime? | Когда одобрено расписание |

### Room
| Field | Type | Notes |
|-------|------|-------|
| id | UUID | PK |
| clustering_run_id | UUID | FK → ClusteringRun |
| name | str | Название зала |

### ExpertRoomAssignment
| Field | Type | Notes |
|-------|------|-------|
| id | UUID | PK |
| room_id | UUID | FK → Room |
| expert_id | UUID | FK → User |
| clustering_run_id | UUID | FK → ClusteringRun |
| status | str | proposed / sent / confirmed / declined |

### Notification
| Field | Type | Notes |
|-------|------|-------|
| id | UUID | PK |
| event_id | UUID | FK → Event |
| type | str | reminder / briefing / ... |
| sent_at | datetime? | |

## Изменения в существующих сущностях

### User (модификация)

Добавить поле:

| Field | Type | Notes |
|-------|------|-------|
| source | str? | "bot" (default) / "import". Источник создания записи |

**Migration**: `ALTER TABLE users ADD COLUMN source VARCHAR(10) DEFAULT 'bot'`

## Новые API-схемы (не DB-модели)

### ProjectStats (response schema)
| Field | Type | Notes |
|-------|------|-------|
| total | int | Общее количество проектов |

### PartnerStats (response schema)
| Field | Type | Notes |
|-------|------|-------|
| total | int | Все партнёры |
| from_bot | int | Созданные через бота |
| from_import | int | Загруженные через импорт |

### DashboardResponse (расширение)

Добавляемые поля (к существующим students, experts, guests, rooms, alerts):

| Field | Type | Notes |
|-------|------|-------|
| projects | ProjectStats | Статистика проектов |
| partners | PartnerStats | Статистика партнёров с разбивкой по источнику |
| event | EventSummary? | null если нет активного события |

### EventSummary (response schema)
| Field | Type | Notes |
|-------|------|-------|
| name | str | Название |
| start_date | date | Дата начала |
| end_date | date | Дата окончания |
| days_until | int | Дней до начала (отрицательное = прошло) |

### PipelineStatusResponse (response schema)
| Field | Type | Notes |
|-------|------|-------|
| phases | list[Phase] | 3 фазы pipeline |
| next_action | NextAction? | Следующий незавершённый шаг (null если всё готово) |

### Phase (response schema)
| Field | Type | Notes |
|-------|------|-------|
| name | str | "data" / "distribution" / "launch" |
| label | str | "Данные" / "Распределение" / "Запуск" |
| status | str | "completed" / "in_progress" / "not_started" |
| steps | list[Step] | Подшаги фазы |

### Step (response schema)
| Field | Type | Notes |
|-------|------|-------|
| name | str | "event" / "projects" / "students" / "experts" / "clustering" / "matching" / "schedule" / "reminders" / "briefing" |
| label | str | Человекочитаемое название |
| status | str | "completed" / "not_started" |

### NextAction (response schema)
| Field | Type | Notes |
|-------|------|-------|
| step | str | Имя шага |
| label | str | Текст подсказки |
| link | str | Путь для навигации |

### RoomCoverage (модификация)

Изменение поля `coverage_status`:

| Old value | New value | Expert count |
|-----------|-----------|-------------|
| "none" | "gap" | 0 |
| "partial" | "partial" | 1 |
| "full" | "covered" | 2 |
| — | "excellent" | 3 |
| — | "excess" | >3 |

## State Transitions

### Pipeline Phase Status
```
not_started → in_progress → completed
```
- Phase = "not_started": ни один шаг не завершён
- Phase = "in_progress": хотя бы один шаг завершён, но не все
- Phase = "completed": все шаги завершены

### Pipeline Step Status
```
not_started → completed
```
Бинарный: шаг либо выполнен, либо нет. Определяется наличием данных в БД.
