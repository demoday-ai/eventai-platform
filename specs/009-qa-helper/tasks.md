# Tasks: Q&A Helper (EPIC-009)

**Input**: Design documents from `/specs/009-qa-helper/`
**Prerequisites**: plan.md (required), spec.md (required)
**Dependencies**: EPIC-005, EPIC-006

## Phase 1: Data Model

- [X] T001 Create migration 009_qa_suggestion.py with qa_suggestions table
- [X] T002 Create QuestionType enum in new qa_suggestion.py model
- [X] T003 Create QASuggestion model with user_id, project_id, questions JSON
- [X] T004 Export model in backend/app/models/__init__.py

**Checkpoint**: QASuggestion entity exists and migrated. ✓

---

## Phase 2: Q&A Service

- [X] T005 Create qa_service.py with `get_question_type(user)` function
- [X] T006 Implement `build_guest_prompt(user, project)` for guest questions
- [X] T007 Implement `build_business_prompt(user, project)` for business questions
- [X] T008 Implement `generate_questions(user_id, project_id)` with LLM call
- [X] T009 Implement caching logic (check expires_at, return cached if valid)
- [X] T010 Implement `get_or_generate_questions(user_id, project_id)` wrapper

**Checkpoint**: Questions can be generated and cached. ✓

---

## Phase 3: Comparison Matrix

- [X] T011 Implement `get_default_criteria(user)` based on profile
- [X] T012 Implement `build_matrix_prompt(user, projects, criteria)`
- [X] T013 Implement `generate_comparison_matrix(user_id, project_ids)` with LLM
- [X] T014 Implement `format_matrix_text(matrix)` for Telegram display

**Checkpoint**: Comparison matrix can be generated. ✓

---

## Phase 4: Bot Handlers

- [X] T015 Create qa.py handler with `/questions` command
- [X] T016 Add role check (guest/business only, not expert)
- [X] T017 Implement project list display from recommendations
- [X] T018 Implement project selection callback with question display
- [X] T019 Add "More questions" / "Back" navigation
- [X] T020 Create `/compare` command handler
- [X] T021 Implement multi-select project flow (max 5)
- [X] T022 Display matrix and "Add criterion" button
- [X] T023 Register handlers in app.py

**Checkpoint**: /questions and /compare commands work. ✓

---

## Phase 5: Polish & Edge Cases

- [X] T024 Handle no recommendations case (suggest /profile)
- [X] T025 Handle LLM timeout with retry and fallback
- [X] T026 Add comprehensive logging
- [X] T027 Update tasks.md marking completed tasks

---

## Dependencies & Execution Order

- Phase 1 → Phase 2
- Phase 2 → Phase 3, Phase 4 (parallel after T010)
- Phase 4 → Phase 5

**STATUS: COMPLETE** ✅
