# Implementation Plan: Dashboard и прогресс

**Branch**: `019-admin-dashboard` | **Date**: 2026-02-09 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/019-admin-dashboard/spec.md`

## Summary

Переработка Dashboard админ-панели EventAI: empty state для первого входа, Global Stepper с 3 фазами подготовки (Данные → Распределение → Запуск), Quick Action с подсказкой следующего шага, 5 карточек метрик (проекты, студенты, эксперты, партнёры, залы), дата + обратный отсчёт, таблица покрытия залов с 5-уровневой шкалой, auto-refresh каждые 30-60 сек. Требуется доработка backend (расширение dashboard endpoint + новый pipeline-status endpoint) и переработка frontend Dashboard компонента.

## Technical Context

**Language/Version**: Python 3.12+ (backend), TypeScript 5.9 (frontend)
**Primary Dependencies**:
- Backend: FastAPI, SQLAlchemy 2.0, asyncpg, Alembic
- Frontend: React 19, TanStack Query 5, React Router v7, Tailwind CSS 4, shadcn/ui, Lucide React
**Storage**: PostgreSQL 16 (существующая БД с таблицами: events, projects, clustering_runs, rooms, expert_room_assignments, participation_requests, schedule_slots, notifications)
**Testing**: pytest + pytest-asyncio (backend), Vitest + Testing Library (frontend)
**Target Platform**: Desktop web (min 1280px)
**Project Type**: web (backend + frontend monorepo)
**Performance Goals**: Dashboard загрузка < 2 сек, auto-refresh каждые 30-60 сек без мерцания
**Constraints**: Только frontend-рефакторинг + минимальные backend-изменения (2 endpoint'а). Никаких новых зависимостей. Desktop-only.
**Scale/Scope**: 3-5 одновременных организаторов, до 330 проектов, до 30 залов

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Pre-research check (Phase 0 gate)

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Layered Architecture | PASS | Backend: Routes → Services → Repos → Models. Новый endpoint следует pattern dashboard.py → dashboard_service.py |
| II. Async-First | PASS | Все DB-запросы через asyncpg + SQLAlchemy async sessions. Frontend: TanStack Query async |
| III. Test-Driven Development | PASS | Backend: pytest + httpx.AsyncClient. Frontend: Vitest + Testing Library. Min 80% coverage |
| IV. Monorepo Conventions | PASS | backend/ и frontend/ — независимые. Schemas в backend/app/schemas/, typed API client в frontend |
| V. AI-First Product | N/A | Dashboard не использует LLM напрямую |
| VI. Data Privacy | PASS | Dashboard отображает агрегаты, не персональные данные. Telegram ID только в header |
| VII. Simplicity & YAGNI | PASS | Минимальные backend-изменения: расширение 1 существующего endpoint + 1 новый. Нет новых зависимостей |

**Gate result: PASS** — нет нарушений.

### Post-design re-check (Phase 1 gate)

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Layered Architecture | PASS | Контракты подтверждают: роуты в dashboard.py, логика в dashboard_service.py, модели без изменений. Новый pipeline-status endpoint следует тому же паттерну |
| II. Async-First | PASS | Все DB-запросы в dashboard_service — async (SQLAlchemy async session). Frontend: TanStack Query с refetchInterval |
| III. Test-Driven Development | PASS | План включает test_admin_dashboard.py (backend) + Dashboard.test.tsx (frontend). TDD-цикл сохранён |
| IV. Monorepo Conventions | PASS | Новые Pydantic-схемы в backend/app/schemas/admin.py. Typed API client в frontend/src/lib/api-client.ts. Миграция через Alembic (source field) |
| V. AI-First Product | N/A | Без изменений |
| VI. Data Privacy | PASS | API возвращает только агрегаты (counts, statuses). Персональные данные не передаются на Dashboard |
| VII. Simplicity & YAGNI | PASS | Нет новых зависимостей. User.source — единственное изменение модели. 6 frontend-компонентов обоснованы переиспользованием GlobalStepper в layout |

**Gate result: PASS** — дизайн Phase 1 соответствует всем принципам конституции.

## Project Structure

### Documentation (this feature)

```text
specs/019-admin-dashboard/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (OpenAPI)
│   ├── dashboard-api.yaml
│   └── pipeline-status-api.yaml
└── checklists/
    └── requirements.md  # Spec quality checklist
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── api/admin/
│   │   └── dashboard.py          # MODIFY: add pipeline-status endpoint
│   ├── schemas/
│   │   └── admin.py              # MODIFY: add PipelineStatusResponse, extend DashboardResponse
│   ├── services/admin/
│   │   └── dashboard_service.py  # MODIFY: add get_pipeline_status(), extend get_dashboard_stats()
│   └── models/                   # NO CHANGES (all data already in DB)
└── tests/
    └── test_admin_dashboard.py   # ADD: tests for new/modified endpoints

frontend/
├── src/
│   ├── pages/
│   │   ├── Dashboard.tsx         # REWRITE: new Dashboard with all 7 user stories
│   │   └── Dashboard.test.tsx    # REWRITE: tests for new Dashboard
│   ├── components/
│   │   ├── dashboard/            # ADD: extracted Dashboard sub-components
│   │   │   ├── EmptyState.tsx
│   │   │   ├── GlobalStepper.tsx
│   │   │   ├── QuickAction.tsx
│   │   │   ├── MetricCards.tsx
│   │   │   ├── EventCountdown.tsx
│   │   │   └── CoverageTable.tsx
│   │   └── layout/
│   │       └── AppLayout.tsx     # MODIFY: add GlobalStepper to header
│   ├── lib/
│   │   └── api-client.ts         # MODIFY: add getPipelineStatus(), update DashboardData type
│   └── hooks/
│       └── usePipelineStatus.ts  # ADD: TanStack Query hook for pipeline status
└── tests/                        # Component tests co-located with components
```

**Structure Decision**: Web application (Option 2). Следуем существующей структуре монорепо. Dashboard sub-components выносятся в `components/dashboard/` для переиспользования GlobalStepper в layout.

## Complexity Tracking

Нет нарушений конституции — таблица не требуется.
