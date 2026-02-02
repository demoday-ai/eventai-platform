# Tasks: Business Partner Profiling & Personalized Program

**Input**: Design documents from `/specs/002-business-profiling/`
**Prerequisites**: plan.md, spec.md, data-model.md, contracts/profiles-api.yaml, research.md
**Tests**: Not explicitly requested — tests are OPTIONAL in this task list

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Project type**: Web application (backend monolith)
- **Source root**: `backend/`
- **Tests root**: `backend/tests/`

---

## Phase 1: Setup

**Purpose**: Database schema and project structure

- [x] T001 Create Alembic migration 003_business_profiles.py in backend/alembic/versions/003_business_profiles.py
- [x] T002 [P] Create BusinessObjective enum and BusinessProfile model in backend/app/models/business_profile.py
- [x] T003 [P] Create ProjectRecommendation model in backend/app/models/project_recommendation.py
- [x] T004 Update models __init__.py to export new models in backend/app/models/__init__.py
- [ ] T005 Run migration: `alembic upgrade head` (manual step)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T006 Create Pydantic schemas for profile create/response in backend/app/schemas/profile.py
- [x] T007 [P] Create profile_service.py with CRUD operations (create, get, update profile) in backend/app/services/profile_service.py
- [x] T008 [P] Create recommendation_service.py skeleton with generate/get methods in backend/app/services/recommendation_service.py
- [x] T009 Add profiling keyboards to backend/app/bot/keyboards.py: objective_keyboard(), industries_keyboard(), stages_keyboard(), confirm_profile_keyboard()

**Checkpoint**: Foundation ready — user story implementation can now begin

---

## Phase 3: User Story 1 — Business Partner Profiling (Priority: P1) 🎯 MVP

**Goal**: Partners can select objective, criteria, and confirm profile via Telegram bot

**Independent Test**: Complete profiling flow with different objectives (investor vs HR), verify profile saved correctly in DB

### Implementation for User Story 1

- [x] T010 [US1] Create business_profiling.py handler skeleton with 6 conversation states in backend/app/bot/handlers/business_profiling.py
- [x] T011 [US1] Implement CHOOSE_OBJECTIVE state: show 4 objective buttons, handle selection in backend/app/bot/handlers/business_profiling.py
- [x] T012 [US1] Implement CHOOSE_CRITERIA state: dynamic criteria buttons based on objective in backend/app/bot/handlers/business_profiling.py
- [x] T013 [US1] Implement FREE_TEXT_INPUT state: MessageHandler for text + "Пропустить" button in backend/app/bot/handlers/business_profiling.py
- [x] T014 [US1] Implement LLM profile extraction in profile_service.extract_from_text() using llm_client in backend/app/services/profile_service.py
- [x] T015 [US1] Implement CONFIRM_PROFILE state: show extracted profile, handle confirm/edit in backend/app/bot/handlers/business_profiling.py
- [x] T016 [US1] Implement profile save on confirmation in profile_service.create_or_update() in backend/app/services/profile_service.py
- [x] T017 [US1] Register business profiling handler in bot app in backend/app/bot/app.py
- [x] T018 [US1] Add graceful degradation: fallback to structured-only input when LLM fails in backend/app/bot/handlers/business_profiling.py

**Checkpoint**: US1 complete — partners can profile themselves, profile stored in DB

---

## Phase 4: User Story 2 — Business-Oriented Project Selection (Priority: P2)

**Goal**: Generate and display ranked project recommendations after profiling

**Independent Test**: After profiling as investor (FinTech, MVP stage), verify top-5 recommendations match criteria

**Depends on**: US1 (profile must exist to generate recommendations)

### Implementation for User Story 2

- [x] T019 [US2] Implement tag-based filtering in recommendation_service.filter_by_tags() in backend/app/services/recommendation_service.py
- [x] T020 [US2] Implement LLM ranking in recommendation_service.rank_with_llm() in backend/app/services/recommendation_service.py
- [x] T021 [US2] Implement recommendation_service.generate_recommendations() combining filter + rank in backend/app/services/recommendation_service.py
- [x] T022 [US2] Implement VIEW_RECOMMENDATIONS state: paginated project list (5/page) in backend/app/bot/handlers/business_profiling.py
- [x] T023 [US2] Add recommendation keyboards: recommendations_page_keyboard(), project_card_keyboard() in backend/app/bot/keyboards.py
- [x] T024 [US2] Implement PROJECT_DETAIL state: show full project info with Подробнее/Назад in backend/app/bot/handlers/business_profiling.py
- [x] T025 [US2] Implement bookmark toggle in recommendation_service.toggle_bookmark() in backend/app/services/recommendation_service.py
- [x] T026 [US2] Add graceful degradation: show tag-filtered results when LLM ranking fails in backend/app/services/recommendation_service.py

**Checkpoint**: US2 complete — partners see ranked recommendations after profiling

---

## Phase 5: User Story 3 — Profile Modification (Priority: P3)

**Goal**: Partners can edit profile and regenerate recommendations

**Independent Test**: After viewing recommendations, change objective from "Инвестиции" to "Найм", verify new recommendations differ

**Depends on**: US1 (profile exists), US2 (recommendations visible)

### Implementation for User Story 3

- [x] T027 [US3] Add "Изменить профиль" button to recommendations view in backend/app/bot/handlers/business_profiling.py
- [x] T028 [US3] Implement EDIT_PROFILE state: show current values, allow field editing in backend/app/bot/handlers/business_profiling.py
- [x] T029 [US3] Implement profile update + recommendation regeneration flow in backend/app/bot/handlers/business_profiling.py
- [x] T030 [US3] Add /profile command handler to access profile edit directly in backend/app/bot/handlers/business_profiling.py

**Checkpoint**: US3 complete — full profile lifecycle implemented

---

## Phase 6: API Endpoints

**Purpose**: REST API for profile management (per contracts/profiles-api.yaml)

- [x] T031 [P] Create profiles.py router with POST /profiles/business endpoint in backend/app/api/profiles.py
- [x] T032 [P] Add GET /profiles/business endpoint in backend/app/api/profiles.py
- [x] T033 [P] Add POST /profiles/business/extract endpoint in backend/app/api/profiles.py
- [x] T034 [P] Add GET /profiles/business/{profile_id}/recommendations endpoint in backend/app/api/profiles.py
- [x] T035 [P] Add POST /profiles/business/{profile_id}/recommendations (regenerate) endpoint in backend/app/api/profiles.py
- [x] T036 [P] Add PATCH /profiles/business/{profile_id}/recommendations/{id} endpoint in backend/app/api/profiles.py
- [x] T037 Register profiles router in main.py in backend/app/main.py

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Error handling, logging, edge cases

- [x] T038 Add edge case handling: empty projects database message in backend/app/bot/handlers/business_profiling.py
- [x] T039 Add edge case handling: no matching projects — suggest broadening criteria in backend/app/services/recommendation_service.py
- [x] T040 Add profiling interruption recovery: continue or restart on return in backend/app/bot/handlers/business_profiling.py
- [x] T041 Add logging for profiling flow and recommendation generation in backend/app/services/profile_service.py and recommendation_service.py
- [ ] T042 Validate quickstart.md flow works end-to-end (manual validation)

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1: Setup ──────────────────────────────────> [Must complete first]
     │
     ▼
Phase 2: Foundational ───────────────────────────> [Blocks all user stories]
     │
     ├──> Phase 3: US1 (Profiling) ─────────────> [Can start after Phase 2]
     │         │
     │         ▼
     │    Phase 4: US2 (Recommendations) ───────> [Depends on US1]
     │         │
     │         ▼
     │    Phase 5: US3 (Modification) ──────────> [Depends on US1 + US2]
     │
     └──> Phase 6: API Endpoints ───────────────> [Can run parallel to bot work]
              │
              ▼
         Phase 7: Polish ───────────────────────> [After all stories]
```

### User Story Dependencies

- **US1 (P1)**: Can start after Phase 2 — No dependencies on other stories
- **US2 (P2)**: Depends on US1 — needs profile to exist for recommendations
- **US3 (P3)**: Depends on US1 + US2 — needs profile and recommendations to modify

### Within Each User Story

- Services before handlers (handler calls service)
- Core implementation before edge cases
- Commit after each task or logical group

### Parallel Opportunities

- T002 + T003: Both models can be created in parallel
- T007 + T008: Both services can be scaffolded in parallel
- T031-T036: All API endpoints can be created in parallel (after services exist)

---

## Parallel Example: Phase 1

```bash
# Launch model creation in parallel:
Task: T002 "Create BusinessProfile model"
Task: T003 "Create ProjectRecommendation model"

# Then sequential:
Task: T004 "Update __init__.py"
Task: T005 "Run migration"
```

## Parallel Example: Phase 6

```bash
# All API endpoints can be developed in parallel:
Task: T031 "POST /profiles/business"
Task: T032 "GET /profiles/business"
Task: T033 "POST /profiles/business/extract"
Task: T034 "GET recommendations"
Task: T035 "POST regenerate"
Task: T036 "PATCH recommendation"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T005)
2. Complete Phase 2: Foundational (T006-T009)
3. Complete Phase 3: User Story 1 (T010-T018)
4. **STOP and VALIDATE**: Test profiling flow with real bot
5. Deploy/demo if ready — partners can create profiles

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. Add US1 → Profiling works → Demo MVP
3. Add US2 → Recommendations visible → Demo v2
4. Add US3 → Full lifecycle → Demo v3
5. Add API + Polish → Complete feature

### Estimated Task Count

| Phase | Tasks | Parallel Opportunities |
|-------|-------|----------------------|
| Setup | 5 | 2 (T002, T003) |
| Foundational | 4 | 2 (T007, T008) |
| US1 | 9 | 0 (sequential flow) |
| US2 | 8 | 0 (sequential flow) |
| US3 | 4 | 0 (sequential flow) |
| API | 7 | 6 (T031-T036) |
| Polish | 5 | 0 |
| **Total** | **42** | **10** |

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
