# Tasks: Загрузка и AI-кластеризация проектов

**Input**: Design documents from `/specs/002-project-clustering/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/clustering-api.yaml

**Tests**: Not explicitly requested — test tasks omitted. Add manually if TDD desired.

**Organization**: Tasks grouped by user story. US4 (seed data) merged into Phase 2 as foundational prerequisite for demo.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)
- Exact file paths included in descriptions

## Path Conventions

- **Backend**: `backend/app/` (models, services, api, bot, schemas)
- **Migrations**: `backend/alembic/versions/`
- **Seed data**: `data/seed/`
- **Scripts**: `scripts/`

---

## Phase 1: Setup

**Purpose**: New dependencies, config, shared infrastructure for EPIC-002

- [x] T001 Add httpx dependency to backend/pyproject.toml (for OpenRouter API client)
- [x] T002 [P] Add OpenRouter config vars to backend/app/config.py: OPENROUTER_API_KEY, OPENROUTER_BASE_URL, OPENROUTER_MODEL
- [x] T003 [P] Add .env.example entries for new env vars in backend/.env.example

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Database models and migration shared by all user stories. Seed data for demo.

**CRITICAL**: No user story work can begin until this phase is complete.

- [x] T004 Create Project model in backend/app/models/project.py (fields: id, event_id FK, title, description, author, telegram_contact, source; unique constraint on event_id+title)
- [x] T005 [P] Create Tag model in backend/app/models/tag.py (fields: id, name; unique constraint on name)
- [x] T006 [P] Create ProjectTag junction model in backend/app/models/project_tag.py (fields: id, project_id FK, tag_id FK; unique constraint on project_id+tag_id)
- [x] T007 [P] Create ClusteringRun model in backend/app/models/clustering_run.py (fields: id, event_id FK, num_rooms, status enum draft/approved/superseded, feedback, llm_model, created_at, approved_at)
- [x] T008 [P] Create Room model in backend/app/models/room.py (fields: id, clustering_run_id FK, name, theme_rationale, display_order)
- [x] T009 [P] Create RoomProject junction model in backend/app/models/room_project.py (fields: id, room_id FK, project_id FK, is_manual boolean)
- [x] T010 Register all new models in backend/app/models/__init__.py
- [x] T011 Create Alembic migration 002_projects_clustering.py in backend/alembic/versions/ — creates tables: tags, projects, project_tags, clustering_runs, rooms, room_projects (order per data-model.md)
- [x] T012 [P] Create Pydantic schemas in backend/app/schemas/project.py: ProjectUploadRow, UploadResult, UploadError, ReplaceConfirmation, ClusteringRequest, ClusteringResult, RoomSchema, MoveProjectRequest, ProjectResponse
- [x] T013 [US4] Create seed data preparation script scripts/prepare_seed.py — extracts projects from data/test/checkpoint12_anon.xlsx (sheets: 1КР 13.10, tracks), joins tags from docs/00-research/past-demoday-projects.md, outputs data/seed/projects_seed.json
- [x] T014 [US4] Create seed_service.py in backend/app/services/seed_service.py — loads data/seed/projects_seed.json into DB on first startup if no projects exist for current event

**Checkpoint**: Database schema ready, seed data available. User story implementation can begin.

---

## Phase 3: User Story 1 — Загрузка данных о проектах (Priority: P1) MVP

**Goal**: Организатор загружает CSV/JSON файл с проектами через бот. Система валидирует, сообщает итог.

**Independent Test**: Организатор отправляет файл в чат → бот парсит и подтверждает загрузку → данные доступны для просмотра.

### Implementation for User Story 1

- [x] T015 [US1] Implement project_service.py in backend/app/services/project_service.py — functions: parse_csv(), parse_json(), validate_rows() (check 5 mandatory fields per row, detect duplicates by title), save_projects() (bulk insert with tag resolution), get_projects() (list with tags), get_project_count(), delete_all_projects() (for replace flow)
- [x] T016 [US1] Implement upload endpoint POST /api/v1/projects/upload in backend/app/api/projects.py — accepts multipart file (CSV/JSON), calls project_service, returns UploadResult. Organizer-only auth check. Handle replace flow (409 → confirm → re-upload with replace=true)
- [x] T017 [US1] Implement GET /api/v1/projects endpoint in backend/app/api/projects.py — list projects with tags for current event, optional room_id filter and search query
- [x] T018 [US1] Register projects API router in backend/app/main.py (/api/v1/projects)
- [x] T019 [US1] Implement bot handler for file upload in backend/app/bot/handlers/clustering.py — ConversationHandler entry: detect document message from organizer, validate format (CSV/JSON, reject others with "Поддерживаемые форматы: CSV, JSON"), call project_service, show UploadResult summary. State: UPLOAD → CONFIRM_REPLACE (if existing data) → next wizard step
- [x] T020 [US1] Add upload-related keyboards in backend/app/bot/keyboards.py — confirm_replace_keyboard() (Да/Нет), format_error message builder

**Checkpoint**: Организатор может загрузить файл через бот, получить отчёт о валидации. Проекты в БД.

---

## Phase 4: User Story 2 — AI-кластеризация проектов по залам (Priority: P1)

**Goal**: Организатор запускает кластеризацию, система распределяет проекты по тематическим залам через LLM.

**Independent Test**: Организатор нажимает «Запустить кластеризацию» → получает распределение по залам с обоснованиями.

**Depends on**: Phase 3 (projects must be loaded)

### Implementation for User Story 2

- [x] T021 [US2] Implement LLM client in backend/app/services/llm_client.py — async httpx client for OpenRouter API: send_chat_completion(system_prompt, user_prompt, json_mode=True), retry logic (3 attempts, exponential backoff), timeout 120s, fallback model support
- [x] T022 [US2] Implement clustering_service.py in backend/app/services/clustering_service.py — functions: build_clustering_prompt(projects, num_rooms, feedback=None), run_clustering(event_id, num_rooms, feedback) → calls LLM, parses JSON response, validates (each project in exactly 1 room, balance ≤5 diff), saves ClusteringRun + Rooms + RoomProjects. Supersedes previous draft run. get_current_clustering(event_id), get_room_details(room_id)
- [x] T023 [US2] Implement POST /api/v1/clustering/run endpoint in backend/app/api/projects.py — accepts ClusteringRequest (num_rooms, optional feedback), organizer-only, calls clustering_service, returns ClusteringResult
- [x] T024 [US2] Implement GET /api/v1/clustering/current endpoint in backend/app/api/projects.py — returns latest clustering run (draft or approved) for current event
- [x] T025 [US2] Implement bot clustering wizard states in backend/app/bot/handlers/clustering.py — States: CLUSTER_PARAMS (show "Кластеризовать N проектов на K залов?" with room count selector, default 6) → CLUSTERING (send typing action, call clustering_service, show progress message) → VIEW_RESULT (overview: list rooms with name + count + first 3 projects, inline buttons per room)
- [x] T026 [US2] Add clustering keyboards in backend/app/bot/keyboards.py — room_count_keyboard() (buttons: 4, 5, 6, 7, 8), rooms_overview_keyboard(rooms) (button per room), room_detail_keyboard(room_id) (back, перенести, пагинация)

**Checkpoint**: Организатор может запустить кластеризацию, получить результат с обоснованиями. Проекты распределены по залам.

---

## Phase 5: User Story 3 — Просмотр и корректировка кластеризации (Priority: P2)

**Goal**: Организатор просматривает залы, переносит проекты, перегенерирует с NL-фидбэком, утверждает расписание.

**Independent Test**: Организатор видит кластеризацию → переносит проект → утверждает финальное расписание.

**Depends on**: Phase 4 (clustering must exist)

### Implementation for User Story 3

- [x] T027 [US3] Implement move_project() in backend/app/services/clustering_service.py — moves project from current room to target room, sets is_manual=true. Validates: project exists, target room exists, not same room. Recalculates room counts.
- [x] T028 [US3] Implement approve_clustering() in backend/app/services/clustering_service.py — sets status='approved', approved_at=now(). Warns if already approved (status check). Sets previous approved run to 'superseded'.
- [x] T029 [US3] Implement POST /api/v1/clustering/{run_id}/move endpoint in backend/app/api/projects.py — accepts MoveProjectRequest, organizer-only, calls move_project(). Warns if schedule already approved (FR-011).
- [x] T030 [US3] Implement POST /api/v1/clustering/{run_id}/approve endpoint in backend/app/api/projects.py — organizer-only, calls approve_clustering(). Returns 409 if already approved with warning.
- [x] T031 [US3] Implement bot correction and approval states in backend/app/bot/handlers/clustering.py — States: MOVE_PROJECT (select project from room → select target room → confirm move → update VIEW_RESULT), REGENERATE (ask for NL feedback → typing → re-cluster with feedback), APPROVE (confirm "Утвердить расписание?" → call approve → show "Расписание утверждено"). Handle already-approved warning (FR-011).
- [x] T032 [US3] Add correction keyboards in backend/app/bot/keyboards.py — project_list_keyboard(room_id, page) (paginated project list with "Перенести" buttons), target_room_keyboard(exclude_room_id) (rooms to move to), approve_keyboard() ("Утвердить" / "Перегенерировать" / "Назад"), regenerate_feedback_prompt()
- [x] T033 [US3] Implement room detail view with pagination in bot handler — for rooms with >20 projects, paginate with "Ещё" button. Show: project title + tags per line. Header: room name + theme_rationale + count.

**Checkpoint**: Полный workflow: загрузка → кластеризация → корректировка → утверждение. Организатор может пройти весь путь за одну сессию (SC-005).

---

## Phase 6: User Story 4 — Предзагруженные данные для демо (Priority: P1)

**Goal**: При первом входе организатора данные уже загружены из seed. Можно сразу кластеризовать.

**Independent Test**: Организатор открывает бот → видит что 305 проектов загружены → запускает кластеризацию.

**Note**: T013-T014 (seed script + service) already in Phase 2. This phase wires them into the wizard.

### Implementation for User Story 4

- [x] T034 [US4] Integrate seed loading into app startup in backend/app/main.py — in lifespan, after bot init, call seed_service.load_seed_if_empty(). Log result.
- [x] T035 [US4] Update wizard entry in backend/app/bot/handlers/clustering.py — when organizer enters project wizard: check if projects exist, show count + source ("305 проектов (демо-данные)" or "N проектов (загружено)") + "Запустить кластеризацию?" button. If seed data and org uploads own file → seed replaced (US4 scenario 2).

**Checkpoint**: Демо-сценарий 6 февраля работает: бот запускается с seed-данными, организатор сразу видит проекты.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Integration, edge cases, final validation

- [x] T036 Register clustering ConversationHandler in backend/app/bot/app.py — add to bot application alongside onboarding handler
- [x] T037 Add wizard navigation: "Назад" button handling in all clustering states (FR-014) in backend/app/bot/handlers/clustering.py
- [x] T038 Implement edge case handling in backend/app/bot/handlers/clustering.py: empty file (0 projects), <10 projects warning, rooms > projects warning, identical tags fallback, >30 sec progress indicator, re-cluster on approved schedule warning
- [x] T039 [P] Add logging for all key operations in clustering handlers and services: file upload, validation result, clustering start/complete, project move, schedule approval
- [x] T040 Validate quickstart.md flow end-to-end: seed load → bot → wizard → cluster → approve

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (Foundational)**: Depends on Phase 1 — creates DB schema + seed data
- **Phase 3 (US1 Upload)**: Depends on Phase 2 — needs models + schemas
- **Phase 4 (US2 Clustering)**: Depends on Phase 3 — needs loaded projects
- **Phase 5 (US3 Correction)**: Depends on Phase 4 — needs clustering result
- **Phase 6 (US4 Seed Demo)**: Depends on Phase 2 (T013-T014) + Phase 3-4 (wizard exists)
- **Phase 7 (Polish)**: Depends on Phases 3-6

### User Story Dependencies

```
Phase 2 (Foundational + Seed prep)
    ↓
Phase 3 (US1: Upload) ← MVP минимум
    ↓
Phase 4 (US2: Clustering) ← core feature
    ↓
Phase 5 (US3: Correction) + Phase 6 (US4: Seed wiring)
    ↓
Phase 7 (Polish)
```

### Within Each Phase

- Models → Services → API endpoints → Bot handlers → Keyboards
- [P] tasks within same phase can run in parallel

### Parallel Opportunities

**Phase 2**: T004-T009 (all models) can run in parallel. T012 (schemas) parallel with models.
**Phase 3**: T015 (service) + T019-T020 (bot handler + keyboards) can be parallelized after T015.
**Phase 4**: T021 (LLM client) parallel with T022 start (service skeleton).
**Phase 7**: T037-T039 all parallel.

---

## Implementation Strategy

### MVP First (Phase 1-3: Upload Only)

1. Complete Phase 1: Setup (dependencies, config)
2. Complete Phase 2: Foundational (DB models, migration, seed)
3. Complete Phase 3: User Story 1 (file upload + validation)
4. **STOP and VALIDATE**: org can upload file, see validation report

### Core Feature (Phase 4: Clustering)

5. Complete Phase 4: User Story 2 (AI clustering)
6. **STOP and VALIDATE**: org can cluster projects, see rooms with rationale

### Full Feature (Phase 5-6: Correction + Demo)

7. Complete Phase 5: User Story 3 (correction + approval)
8. Complete Phase 6: User Story 4 (seed data wiring)
9. **STOP and VALIDATE**: full demo flow works end-to-end

### Polish (Phase 7)

10. Complete Phase 7: edge cases, navigation, logging
11. **FINAL VALIDATION**: run quickstart.md scenario

---

## Notes

- [P] tasks = different files, no dependencies
- [US*] label maps task to specific user story for traceability
- US4 is split: seed prep (Phase 2) + wizard wiring (Phase 6)
- Bot ConversationHandler is built incrementally across Phases 3-6 (add states per phase)
- Total: 40 tasks across 7 phases
- Commit after each phase completion
