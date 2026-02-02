# Data Model: Онбординг и выбор роли

**Feature**: 001-onboarding
**Date**: 2026-02-02
**Source**: ER v1.1 (`docs/02-specification/08-er-diagram.md`), Spec, Clarifications

---

## Сущности

### users

| Поле | Тип | Constraints | Описание |
|------|-----|-------------|----------|
| id | UUID | PK, default gen | Внутренний идентификатор |
| telegram_user_id | STRING | UNIQUE, NOT NULL | Telegram user ID (числовой, хранится как строка) |
| full_name | STRING | NOT NULL | first_name + last_name из Telegram-профиля |
| username | STRING | NULLABLE | @username из Telegram (может отсутствовать) |
| guest_subtype | ENUM | NULLABLE | applicant / ai_practitioner / other. Заполняется только для роли guest |
| created_at | TIMESTAMP | NOT NULL, default now | Дата первого /start |
| updated_at | TIMESTAMP | NOT NULL, auto-update | Дата последнего обновления |

**Правила:**
- При повторном /start — обновить full_name и username из Telegram-профиля (upsert)
- guest_subtype сбрасывается в NULL при смене роли с guest на другую
- email, phone, organization — НЕ заполняются на этапе онбординга (для будущих EPIC)

### roles

| Поле | Тип | Constraints | Описание |
|------|-----|-------------|----------|
| id | UUID | PK | Внутренний идентификатор |
| code | STRING | UNIQUE, NOT NULL | organizer / student / expert / guest / business |
| name | STRING | NOT NULL | Отображаемое название: Организатор / Студент / Эксперт / Гость / Бизнес-партнёр |

**Правила:**
- Справочник из 5 записей, заполняется через seed-миграцию
- Immutable — не изменяется через API

### user_roles

| Поле | Тип | Constraints | Описание |
|------|-----|-------------|----------|
| id | UUID | PK | Внутренний идентификатор |
| user_id | UUID | FK → users.id, NOT NULL | Пользователь |
| role_id | UUID | FK → roles.id, NOT NULL | Роль |
| event_id | UUID | FK → events.id, NOT NULL | Событие |
| created_at | TIMESTAMP | NOT NULL, default now | Дата назначения роли |

**Правила:**
- UNIQUE constraint: (user_id, event_id) — одна роль на пользователя на событие
- При смене роли — UPDATE существующей записи (не DELETE + INSERT)
- При смене с guest на другую роль — также сбросить users.guest_subtype

### events

| Поле | Тип | Constraints | Описание |
|------|-----|-------------|----------|
| id | UUID | PK | Внутренний идентификатор |
| name | STRING | NOT NULL | Название события |
| start_date | DATE | NOT NULL | Дата начала |
| end_date | DATE | NOT NULL | Дата окончания |
| created_at | TIMESTAMP | NOT NULL, default now | Дата создания |

**Правила:**
- Для демо — 1 событие, предзагруженное через seed-миграцию
- Мультисобытийность — Release 1.1

---

## Диаграмма связей

```
users 1──* user_roles *──1 roles
                  *──1 events
```

- User → UserRole: one-to-many (но для одного события — one-to-one через UNIQUE constraint)
- Role → UserRole: one-to-many
- Event → UserRole: one-to-many

---

## State transitions (User onboarding)

```
[Новый пользователь]
     │ /start
     ▼
[Выбор роли] ── организатор ──► [Проверка whitelist]
     │                               │ fail → [Выбор роли]
     │                               │ pass → [Меню организатора]
     ├── студент/эксперт/бизнес ──► [Меню роли]
     │
     └── гость ──► [Выбор подтипа]
                         │
                         ▼
                   [Меню гостя]

[Существующий пользователь]
     │ /start или /role
     ▼
[Продолжить / Сменить роль]
     │ Продолжить → [Меню текущей роли]
     │ Сменить → [Выбор роли] (см. выше)
```
