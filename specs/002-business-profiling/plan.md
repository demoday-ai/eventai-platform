# Implementation Plan: Business Partner Profiling & Personalized Program

**Branch**: `002-business-profiling` | **Date**: 2026-02-02 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/002-business-profiling/spec.md`

## Summary

Implement business partner profiling flow and personalized project recommendations for EPIC-006. Partners select a business objective (Investment/Hiring/Technology/Partnership), provide criteria via inline buttons + optional free text, receive AI-extracted profile confirmation, and get a ranked list of 5-15 relevant projects.

## Technical Context

**Language/Version**: Python 3.12+
**Primary Dependencies**: FastAPI, python-telegram-bot 21.x, SQLAlchemy 2.0, httpx (for OpenRouter)
**Storage**: PostgreSQL 16 (2 new tables: business_profiles, project_recommendations)
**Testing**: pytest + pytest-asyncio
**Target Platform**: Linux server (Yandex Cloud VM, Ubuntu 22.04)
**Project Type**: Web application (backend monolith)
**Performance Goals**: Recommendations within 5 seconds, profile extraction within 3 seconds
**Constraints**: Telegram Bot API limits (4096 chars/message, 64 bytes callback data, 30 msg/sec)
**Scale/Scope**: ~50 business partners, ~330 projects for matching

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Requirement | Status |
|-----------|-------------|--------|
| **I. Telegram-First** | All user actions via inline buttons; free text only for profiling | ✅ PASS — profiling uses buttons + optional free text |
| **I. Telegram-First** | Support Business/партнёр role with adaptive UI | ✅ PASS — role exists in EPIC-001, profiling extends it |
| **I. Telegram-First** | Respect Telegram limits (4096 chars, 64 bytes callback) | ✅ PASS — project cards paginated, callback data compact |
| **II. AI-Augmented** | AI proposes, human approves | ✅ PASS — profile extracted by AI, confirmed by partner |
| **II. AI-Augmented** | Graceful degradation when LLM unavailable | ✅ PASS — see Edge Cases: fallback to structured input |
| **III. Data-Driven** | Use real DD data for testing | ✅ PASS — 400 projects pre-seeded from checkpoint12 |
| **IV. Pragmatic** | YAGNI, minimal abstractions | ✅ PASS — reuses existing llm_client, project_service |
| **IV. Pragmatic** | Demo 6 февраля | ✅ PASS — 4 days remaining, scope is 1 epic |

**Gate Result**: ✅ PASS — All principles satisfied.

## Project Structure

### Documentation (this feature)

```text
specs/002-business-profiling/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (OpenAPI)
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
backend/
├── alembic/versions/
│   └── 003_business_profiles.py      # New migration
├── app/
│   ├── models/
│   │   ├── business_profile.py       # New model
│   │   └── project_recommendation.py # New model
│   ├── services/
│   │   ├── profile_service.py        # New service (CRUD + LLM extraction)
│   │   └── recommendation_service.py # New service (matching + ranking)
│   ├── api/
│   │   └── profiles.py               # New API endpoints
│   ├── bot/
│   │   ├── handlers/
│   │   │   └── business_profiling.py # New handler (ConversationHandler)
│   │   └── keyboards.py              # Extended with profiling keyboards
│   └── schemas/
│       └── profile.py                # New Pydantic schemas
└── tests/
    ├── unit/
    │   └── test_profile_service.py
    └── integration/
        └── test_business_profiling.py
```

**Structure Decision**: Follows existing backend structure from EPIC-001/002. No new directories needed — extends existing models/, services/, api/, bot/handlers/.

## Complexity Tracking

No violations. Design follows established patterns from EPIC-001 (onboarding) and EPIC-002 (clustering).

---

## Post-Design Constitution Re-Check

*Re-evaluated after Phase 1 design completion.*

| Principle | Design Artifact | Status |
|-----------|-----------------|--------|
| **I. Telegram-First** | `business_profiling.py` — 6-state ConversationHandler, inline buttons | ✅ PASS |
| **I. Telegram-First** | Callback data encoding ≤64 bytes (`bp:obj:inv`, `bp:proj:<uuid8>`) | ✅ PASS |
| **II. AI-Augmented** | Profile extraction via `llm_client` + confirmation step | ✅ PASS |
| **II. AI-Augmented** | Graceful degradation: fallback to structured-only input | ✅ PASS |
| **III. Data-Driven** | Matching against 400 pre-seeded projects with tags | ✅ PASS |
| **IV. Pragmatic** | Reuses `llm_client`, `project_service`, keyboard patterns | ✅ PASS |

**Post-Design Gate Result**: ✅ PASS — All principles validated against concrete design.

---

## Generated Artifacts

| Phase | Artifact | Path |
|-------|----------|------|
| 0 | Research | [research.md](./research.md) |
| 1 | Data Model | [data-model.md](./data-model.md) |
| 1 | API Contract | [contracts/profiles-api.yaml](./contracts/profiles-api.yaml) |
| 1 | Quickstart | [quickstart.md](./quickstart.md) |
| 2 | Tasks | [tasks.md](./tasks.md) *(pending — run `/speckit.tasks`)* |
