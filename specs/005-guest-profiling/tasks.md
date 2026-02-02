# Tasks: Профилирование и программа для гостей (EPIC-005)

**Input**: Design documents from `/specs/005-guest-profiling/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- Include exact file paths in descriptions

## Path Conventions

- **Backend**: `backend/app/` (models, services, api, bot)
- **Migrations**: `backend/alembic/versions/`
- **Tests**: `backend/tests/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Database migration and shared models for guest profiling

- [x] T001 [P] Create GuestProfile model in backend/app/models/guest_profile.py per data-model.md (UUID PK, user_id FK, event_id FK, selected_tags JSONB, extracted_tags JSONB, keywords JSONB, raw_text TEXT, updated_at; UNIQUE user_id+event_id)
- [x] T002 [P] Create Recommendation model in backend/app/models/recommendation.py per data-model.md (UUID PK, guest_profile_id FK CASCADE, project_id FK CASCADE, relevance_score FLOAT, category VARCHAR(20), rank INTEGER, llm_summary TEXT; UNIQUE profile+project)
- [x] T003 Register GuestProfile and Recommendation in backend/app/models/__init__.py (add imports and __all__ entries)
- [x] T004 Create Alembic migration 004_guest_profiling in backend/alembic/versions/004_guest_profiling.py (create guest_profiles and recommendations tables with all constraints, indexes; down_revision="003")

**Checkpoint**: Database schema ready for guest profiling

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core service logic that MUST be complete before bot handler or API can work

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T005 Create profiling_service.py in backend/app/services/profiling_service.py with helper functions: get_available_tags(session, event_id) → list of (tag_name, project_count) sorted by project_count desc; get_or_create_profile(session, user_id, event_id) → GuestProfile; save_profile(session, profile, selected_tags, extracted_tags, keywords, raw_text) → GuestProfile
- [x] T006 Implement extract_interests_from_text(raw_text, available_tags) in backend/app/services/profiling_service.py — calls llm_client.send_chat_completion with text extraction prompt from quickstart.md; returns {"tags": [...], "keywords": [...]}; on LLM failure returns {"tags": [], "keywords": []} (graceful degradation per R3)
- [x] T007 Implement compute_project_idf(session, event_id) in backend/app/services/profiling_service.py — IDF weights per project tags: idf(tag) = log(total_projects / projects_with_tag) per R2; reuses pattern from matching_service.compute_idf_weights but counts projects not experts
- [x] T008 Implement score_projects(session, event_id, profile) in backend/app/services/profiling_service.py — IDF tag overlap scoring: for each project compute sum(idf(tag) for tag in intersection(profile_all_tags, project_tags)); returns list of (project_id, score) sorted desc; profile_all_tags = selected_tags + extracted_tags (deduplicated)
- [x] T009 Implement llm_rerank_projects(profile, candidates_top20) in backend/app/services/profiling_service.py — calls llm_client with re-ranking prompt from quickstart.md; input: top-20 candidates from score_projects; returns reordered list of (project_id, score); on LLM failure returns candidates unchanged (graceful degradation per R1)
- [x] T010 Implement generate_llm_summaries(profile, projects_top15) in backend/app/services/profiling_service.py — single LLM call per R4: batch generates 2-3 sentence summaries for 15 projects adapted to guest profile; on LLM failure returns None for each summary (fallback: first 2 sentences of original description handled in caller)
- [x] T011 Implement generate_recommendations(session, profile) in backend/app/services/profiling_service.py — orchestrator: 1) compute IDF scores for all projects, 2) take top-20 → LLM rerank → take top-15, 3) generate LLM summaries, 4) if <10 matching: pad with popular projects per FR-013, 5) split into must_visit (top-5) and if_time (rest), 6) delete old recommendations for profile, 7) save new Recommendation rows with rank/category/score/llm_summary, 8) return structured result
- [x] T012 Implement get_recommendations(session, profile_id) in backend/app/services/profiling_service.py — load existing recommendations for profile with project details (title, description, author, telegram_contact, tags, room_name, room_number); split into must_visit/if_time; add conflict_rooms detection (projects from different rooms in same selection)
- [x] T013 Implement get_project_detail(session, profile_id, project_id) in backend/app/services/profiling_service.py — load full project detail for a project in the guest's recommendation list; include room info from approved clustering via room_projects

**Checkpoint**: Foundation ready — all profiling service logic available for bot and API

---

## Phase 3: User Story 1 — Указание интересов гостем (Priority: P1) 🎯 MVP

**Goal**: Guest specifies interests via hybrid UI (inline tag buttons + free text), AI extracts profile, guest confirms

**Independent Test**: Guest with role "AI-практик" enters bot, selects NLP + CV tags, types "антифрод", confirms profile → profile saved in DB with selected_tags=["NLP","CV"], extracted_tags containing FinTech-related tags, keywords=["антифрод"]

### Implementation for User Story 1

- [x] T014 [P] [US1] Add profiling keyboards to backend/app/bot/keyboards.py: tag_selection_keyboard(tags, selected) → InlineKeyboardMarkup with 3-column grid of toggle buttons (✓/plain), "Готово" and "Написать текстом" buttons; callback data "ptag:{tag_name_truncated}" (≤64 bytes); confirm_profile_keyboard() → [Да] [Нет, изменить]; start_profiling_keyboard() → [Начать профилирование]; generate_program_keyboard() → [Сгенерировать программу] [Позже]
- [x] T015 [US1] Create guest_profiling.py ConversationHandler in backend/app/bot/handlers/guest_profiling.py with states: CHOOSE_TAGS, ENTER_TEXT, CONFIRM_PROFILE (states from quickstart.md conversation flow); entry point: /profile command + callback "start_profiling"; CHOOSE_TAGS state: handle ptag: toggle callbacks (update selected set in context.user_data, re-render keyboard), handle "Готово" button → if raw_text present call extract_interests_from_text → go to CONFIRM_PROFILE; handle free text message → save to context.user_data["raw_text"] → call extract_interests_from_text → go to CONFIRM_PROFILE
- [x] T016 [US1] Implement CONFIRM_PROFILE state in backend/app/bot/handlers/guest_profiling.py: show "Вас интересует: {all_interests}. Верно?" with confirm_profile_keyboard(); "Да" → save_profile() via profiling_service → send "Профиль сохранён!" with generate_program_keyboard() → END or GENERATE_PROGRAM; "Нет, изменить" → return to CHOOSE_TAGS with previous selections preserved in context.user_data
- [x] T017 [US1] Handle edge cases in guest_profiling.py: empty profile (no tags, no text) → "Укажите хотя бы один интерес" per edge case; AI extraction failure → "Текст не удалось обработать, используем выбранные тематики" per FR-003; user without guest/business role → "Профилирование доступно только гостям" per FR-014
- [x] T018 [US1] Add auto-trigger after onboarding in backend/app/bot/handlers/start.py: after subtype_chosen() for Guest role, send additional message "Укажите интересы для персональной программы" with start_profiling_keyboard(); also after role_chosen() for Business role per FR-014
- [x] T019 [US1] Register profiling handler in backend/app/bot/app.py: import get_profiling_handler from guest_profiling; add application.add_handler(get_profiling_handler()) before standalone callbacks
- [x] T020 [US1] Add REST endpoints in backend/app/api/guests.py: GET /api/v1/profile → get profile for current user; POST /api/v1/profile → create/update profile (calls extract_interests if raw_text); GET /api/v1/profile/tags → available tags with counts; role check: guest or business only
- [x] T021 [US1] Register guests router in backend/app/main.py: import guests router, add app.include_router(guests_router, prefix="/api/v1")

**Checkpoint**: Guest can specify interests, AI extracts them, guest confirms, profile saved. Bot and API both work.

---

## Phase 4: User Story 2 — Генерация персональной программы (Priority: P1)

**Goal**: After profile confirmed, generate personalized program of 10-15 projects ranked by relevance with LLM summaries

**Independent Test**: Guest with profile "NLP, антифрод" triggers generation → receives list of 10-15 projects split into must_visit (5) and if_time (rest), each with AI-adapted summary, room info, tags

### Implementation for User Story 2

- [x] T022 [US2] Add GENERATE_PROGRAM and VIEW_PROGRAM states to ConversationHandler in backend/app/bot/handlers/guest_profiling.py: GENERATE_PROGRAM → call generate_recommendations() from profiling_service (show typing indicator); VIEW_PROGRAM → format and display recommendations: "🎯 Обязательно посетить:" (top-5) + "⏰ Если останется время:" (rest); each item: rank, title, summary (llm_summary or first 2 sentences of description), room, tags, author; add inline buttons "Подробнее: N" for each project + "Обновить профиль"
- [x] T023 [US2] Handle Telegram 4096 char limit in VIEW_PROGRAM: if formatted message exceeds 4096 chars, split into multiple messages — first message: must_visit projects, second: if_time projects; attach navigation keyboard to last message only
- [x] T024 [US2] Implement program_recommendation_keyboard(recommendations) in backend/app/bot/keyboards.py: inline buttons for "Подробнее" per project (callback "pdetail:{project_id_short}"), paginated if >8 buttons; "Обновить профиль" button (callback "profile:update"); "Назад" if in detail view
- [x] T025 [US2] Add room conflict detection in VIEW_PROGRAM display: mark projects from different rooms that are in parallel with "⚠️ Параллельно с Зал N" per FR-009 and R7; compute conflict_rooms from room assignments of recommended projects
- [x] T026 [US2] Add REST endpoints for recommendations in backend/app/api/guests.py: POST /api/v1/recommendations → generate_recommendations(); GET /api/v1/recommendations → get existing recommendations; both require existing profile (400 if missing)
- [x] T027 [US2] Handle graceful degradation in generate flow: if LLM reranking fails → use tag-only scores; if LLM summaries fail → use first 2 sentences of project.description; if <10 matching projects → pad with popular projects (most tags, most rooms) per FR-013; log all fallback activations

**Checkpoint**: Full profiling → program generation flow works end-to-end. Guest gets personalized project list.

---

## Phase 5: User Story 3 — Просмотр деталей проекта из подборки (Priority: P2)

**Goal**: Guest can drill into any project from the recommendation list to see full details

**Independent Test**: Guest with existing recommendation list clicks "Подробнее: 3" → sees full description, all tags, author, Telegram contact, room; clicks "Назад" → returns to recommendation list

### Implementation for User Story 3

- [x] T028 [US3] Add VIEW_DETAIL state to ConversationHandler in backend/app/bot/handlers/guest_profiling.py: handle "pdetail:{project_id_short}" callback → call get_project_detail() → display: title, full description, all tags, author, telegram_contact, room name + number, relevance score %, llm_summary if available; add "Назад к программе" button
- [x] T029 [US3] Add REST endpoint GET /api/v1/recommendations/{project_id} in backend/app/api/guests.py per contracts: return ProjectDetailResponse with full project info + room + relevance score
- [x] T030 [US3] Handle "Назад к программе" callback in VIEW_DETAIL → return to VIEW_PROGRAM state, re-display the recommendation list from saved context (not re-generate)

**Checkpoint**: Guest can browse recommendation details and navigate back. Full drill-down works.

---

## Phase 6: User Story 4 — Обновление профиля и перегенерация (Priority: P3)

**Goal**: Guest can update interests at any time and get a new recommendation list

**Independent Test**: Guest with existing profile sends /profile → sees current interests → updates → confirms → new program generated with updated results

### Implementation for User Story 4

- [x] T031 [US4] Handle /profile command for existing users in backend/app/bot/handlers/guest_profiling.py: if profile exists → show "Ваш текущий профиль: {interests}. Обновить?" with [Да, обновить] [Нет]; "Да" → go to CHOOSE_TAGS with previous selected_tags pre-selected in context; "Нет" → END
- [x] T032 [US4] Handle "profile:update" callback from VIEW_PROGRAM in backend/app/bot/handlers/guest_profiling.py: same as /profile for existing user — go to CHOOSE_TAGS with previous tags pre-selected; after new profile confirmed → auto-generate new recommendations (delete old, create new)
- [x] T033 [US4] Ensure save_profile in profiling_service.py handles upsert correctly: if profile exists for user+event, update fields; delete old recommendations when profile updated per spec (cached until profile update)

**Checkpoint**: Full cycle works: profile → program → details → update → new program.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Validation, edge cases, integration completeness

- [x] T034 Validate all Python files compile successfully: run py_compile on all new/modified files (guest_profile.py, recommendation.py, profiling_service.py, guest_profiling.py, guests.py, keyboards.py, app.py, main.py, start.py, __init__.py)
- [x] T035 Verify ConversationHandler state machine completeness: ensure all states have fallback handlers, /cancel works from any state, timeout handling per python-telegram-bot patterns
- [x] T036 Add logging throughout profiling_service.py: log LLM calls (success/failure/fallback), profile save/update, recommendation generation timing, edge cases triggered
- [x] T037 Test graceful degradation paths: verify code handles LLM timeout (120s), LLM JSON parse error, empty project list, no approved clustering, user with no role

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (Foundational)**: Depends on Phase 1 (models must exist for service imports)
- **Phase 3 (US1)**: Depends on Phase 2 (service functions needed for bot handler)
- **Phase 4 (US2)**: Depends on Phase 2 + Phase 3 (needs profile to exist before generating program)
- **Phase 5 (US3)**: Depends on Phase 4 (needs recommendations to drill into)
- **Phase 6 (US4)**: Depends on Phase 3 + Phase 4 (needs profile + recommendations to update)
- **Phase 7 (Polish)**: Depends on all user stories being complete

### User Story Dependencies

- **US1 (P1)**: Can start after Phase 2 — no dependencies on other stories
- **US2 (P1)**: Depends on US1 (profile must exist to generate recommendations)
- **US3 (P2)**: Depends on US2 (recommendations must exist to view details)
- **US4 (P3)**: Depends on US1 + US2 (update requires existing profile and regeneration)

### Within Each User Story

- Models before services (Phase 1 → Phase 2)
- Services before bot handlers and API endpoints
- Core flow before edge cases
- Bot handler before REST API (bot is primary interface per Constitution I)

### Parallel Opportunities

- T001 and T002 (models) can run in parallel [P]
- T014 (keyboards) can run in parallel with T015-T016 (handler) [P]
- T020 (REST API) can run in parallel with T015-T019 (bot handler) within US1
- T024 (keyboards) and T022-T023 (handler) can overlap
- T026 (REST API) and T022-T025 (bot handler) within US2

---

## Parallel Example: Phase 1

```bash
# Launch both models in parallel:
Task: "Create GuestProfile model in backend/app/models/guest_profile.py"
Task: "Create Recommendation model in backend/app/models/recommendation.py"
```

## Parallel Example: User Story 1

```bash
# Launch keyboards and handler in parallel:
Task: "Add profiling keyboards to backend/app/bot/keyboards.py"
Task: "Create guest_profiling.py ConversationHandler in backend/app/bot/handlers/guest_profiling.py"
```

---

## Implementation Strategy

### MVP First (US1 + US2)

1. Complete Phase 1: Setup (models + migration)
2. Complete Phase 2: Foundational (profiling_service)
3. Complete Phase 3: US1 — Guest can specify interests
4. Complete Phase 4: US2 — Guest gets personalized program
5. **STOP and VALIDATE**: Test full profiling → program flow
6. Demo-ready with core value proposition

### Incremental Delivery

1. Phase 1 + 2 → Foundation ready
2. + US1 → Profile creation works (value: guest data captured)
3. + US2 → Program generation works (MVP! core value delivered)
4. + US3 → Project details browsable (enhanced UX)
5. + US4 → Profile updatable (complete feature)
6. + Polish → Production-quality

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story
- Bot handler is primary interface (Constitution I: Telegram-First)
- REST API mirrors bot functionality for future admin console
- All LLM calls use existing llm_client.py — no new dependencies
- Callback data must be ≤64 bytes (Telegram limit) — use truncated IDs
- 4096 char message limit — split long recommendation lists
- Commit after each task or logical group
