# Specification: Business Follow-up (EPIC-015)

**Version:** 1.0
**Date:** 2026-02-03
**Dependencies:** EPIC-005 (Business Profiling), EPIC-014 (Guest Follow-up)

---

## Problem Statement

Бизнес-партнёры и инвесторы после Demo Day:
- Теряют контакты интересных проектов
- Нет шаблонов для начала переговоров (LOI, NDA)
- Сложно отслеживать pipeline проектов

---

## User Stories

### US-021: Follow-up пакет для бизнес-партнёра
**Как бизнес-партнёр**, я хочу получить структурированный follow-up с шаблонами документов, чтобы быстро начать переговоры.

**Acceptance Criteria:**
- Пакет включает LOI шаблон, адаптированный под мои цели
- Контакты проектов с указанием стадии и релевантности
- Возможность отметить проекты как "в работе"

---

## Functional Requirements

### FR-001: Расширенный follow-up пакет
- Всё из EPIC-014 (Guest Follow-up)
- Дополнительно: LOI шаблон, partnership template

### FR-002: Pipeline tracking
- Статусы: interested, contacted, negotiating, closed
- Заметки по каждому проекту

### FR-003: LOI генерация
- На основе BusinessProfile (objective, budget, timeline)
- Персонализированный шаблон письма

### FR-004: Команда /bizfollowup
- Расширенный пакет для бизнес-партнёров
- Inline-кнопки для статусов проектов

---

## Data Model

### BusinessFollowup (новая сущность)
| Field | Type | Description |
|-------|------|-------------|
| id | UUID | PK |
| user_id | UUID | FK → users (business) |
| event_id | UUID | FK → events |
| project_id | UUID | FK → projects |
| status | Enum | interested/contacted/negotiating/closed |
| notes | Text | Заметки партнёра |
| loi_generated | Boolean | LOI уже сгенерирован |

---

## Success Criteria

- 70% бизнес-партнёров используют follow-up
- Среднее количество проектов в pipeline: 5+
- LOI генерируется за <3 секунды
