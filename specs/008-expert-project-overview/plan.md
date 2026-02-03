# Implementation Plan: Expert Project Overview (EPIC-008)

**Branch**: `008-expert-project-overview` | **Date**: 2026-02-03 | **Spec**: [spec.md](./spec.md)

## Summary

Автоматическая отправка брифинга экспертам за 24 часа до Demo Day. Брифинг содержит карточки проектов комнаты эксперта с информацией о GitHub-статусе и артефактах.

## Technical Context

**Language/Version**: Python 3.12+
**Primary Dependencies**: FastAPI, python-telegram-bot 21.x, SQLAlchemy 2.0, httpx (GitHub API)
**Storage**: PostgreSQL 16
**Target Platform**: Linux server (Yandex Cloud VM)
**Constraints**: Telegram 4096 char limit, GitHub API rate limit (60 req/hour unauthenticated)

## Project Structure

### Source Code

```text
backend/
├── app/
│   ├── services/
│   │   ├── briefing_service.py      # NEW: Briefing logic, card formatting
│   │   └── github_service.py        # NEW: GitHub API client
│   └── bot/
│       └── handlers/
│           └── briefing.py          # NEW: /briefing command handler
└── alembic/
    └── versions/
        └── 008_expert_briefing.py   # NEW: Migration for ExpertBriefing table
```

### Key Decisions

| Aspect | Decision | Rationale |
|--------|----------|-----------|
| GitHub API | Unauthenticated requests | Simple, 60 req/hour sufficient for ~50 experts |
| Message splitting | By project cards | Keep cards intact, split between projects |
| Scheduling | Reuse EPIC-007 scheduler | Already has eve-of-DD job infrastructure |

## Dependencies

- **EPIC-002**: Project data (title, description, tags, stack)
- **EPIC-004**: Expert assignments (expert → room mapping)
- **EPIC-007**: Notification infrastructure, scheduler

## Complexity Tracking

No Constitution Check violations. All principles satisfied.

| Aspect | Decision | Rationale |
|--------|----------|-----------|
| New table | ExpertBriefing | Track delivery status per expert |
| GitHub check | Async httpx | Non-blocking, with timeout |
| Message format | Plain text with emoji | No inline keyboards per spec |
