# Implementation Plan: Дашборд покрытия тематик для организатора (EPIC-006)

**Branch**: `006-organizer-coverage` | **Date**: 2026-02-02 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/006-organizer-coverage/spec.md`

## Summary

Организатор получает дашборд покрытия залов экспертами — через Telegram-бот (`/coverage`) и REST API. Система показывает сводку по залам (покрыт / частично / не покрыт), детализацию с экспертами и тегами, выявляет тематические пробелы (теги проектов без эксперта) и рекомендует свободных экспертов.

**Ключевой факт**: REST API для coverage уже частично реализован в EPIC-004 (`invite_service.get_coverage_dashboard`, `get_room_coverage_detail`). EPIC-006 расширяет его тегово-тематической аналитикой и добавляет Telegram-бот-интерфейс.

## Technical Context

**Language/Version**: Python 3.12+
**Primary Dependencies**: FastAPI, python-telegram-bot 21.x, SQLAlchemy 2.0, Alembic, asyncpg
**Storage**: PostgreSQL 16
**Testing**: Manual validation via bot + API
**Target Platform**: Linux server (Yandex Cloud VM)
**Project Type**: Web (backend-only, bot as client)
**Performance Goals**: <2s response for /coverage (small dataset: ~50 experts, ~6 rooms)
**Constraints**: Telegram 4096 char message limit, 64 byte callback data
**Scale/Scope**: ~50 experts, ~330 projects, ~6-10 rooms, ~5 organizers

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Telegram-First | PASS | `/coverage` bot command + inline drill-down. REST API mirrors for web dashboard |
| II. AI-Augmented, Human-Approved | PASS | Read-only dashboard. No AI actions — pure aggregation queries. No LLM dependency |
| III. Data-Driven | PASS | Uses existing ExpertRoomAssignment, tags, rooms data from EPIC-002/004 |
| IV. Pragmatic Development | PASS | Extends existing `invite_service` coverage functions. No new models needed. Minimal new code |

No violations. No complexity tracking needed.

## Project Structure

### Documentation (this feature)

```text
specs/006-organizer-coverage/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── api.yaml
└── tasks.md             # Phase 2 output (via /speckit.tasks)
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── services/
│   │   └── coverage_service.py    # NEW: coverage aggregation + gap analysis
│   ├── api/
│   │   └── experts.py             # MODIFY: update existing coverage endpoints
│   ├── bot/
│   │   ├── handlers/
│   │   │   └── coverage.py        # NEW: /coverage bot command + callbacks
│   │   ├── keyboards.py           # MODIFY: add coverage keyboards
│   │   └── app.py                 # MODIFY: register coverage handler
│   ├── schemas/
│   │   └── coverage.py            # NEW: Pydantic response schemas
│   └── main.py                    # No changes needed (no periodic tasks)
```

**Structure Decision**: Separate `coverage_service.py` from existing `invite_service.py` — the coverage logic is read-only aggregation, while invite_service handles write operations (invites, reminders, escalations). The existing coverage functions in invite_service will be migrated or delegated.
