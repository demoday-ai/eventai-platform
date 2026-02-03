# Tasks: Student Feedback (EPIC-012)

**Dependencies:** EPIC-013 (for expert comments source)

## Phase 1: Data Model

- [ ] T001 Create migration 012_feedback_comment.py
- [ ] T002 Create FeedbackComment model with category enum
- [ ] T003 Create ModerationStatus enum
- [ ] T004 Export in models/__init__.py

## Phase 2: Feedback Service

- [ ] T005 Create feedback_service.py
- [ ] T006 Implement `process_comment(text)` with LLM
- [ ] T007 Implement `get_pending_by_project(project_id)`
- [ ] T008 Implement `approve_feedback(feedback_id)`
- [ ] T009 Implement `reject_feedback(feedback_id)`
- [ ] T010 Implement `send_to_student(project_id, bot)`

## Phase 3: Bot Handler

- [ ] T011 Create feedback.py handler
- [ ] T012 Implement /feedback command (organizer only)
- [ ] T013 Show project list with pending counts
- [ ] T014 Implement feedback review UI
- [ ] T015 Implement approve/reject/edit callbacks
- [ ] T016 Implement send to student
- [ ] T017 Register handlers in app.py

## Phase 4: Polish

- [ ] T018 Format student message nicely
- [ ] T019 Handle edge cases
- [ ] T020 Update tasks.md
