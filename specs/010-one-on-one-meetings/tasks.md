# Tasks: Contact Requests (EPIC-010)

**Input**: Design documents from `/specs/010-one-on-one-meetings/`
**Prerequisites**: plan.md (required), spec.md (required)
**Dependencies**: EPIC-005, EPIC-006

## Phase 1: Data Model

- [X] T001 Create migration 010_contact_request.py with contact_requests table
- [X] T002 Create ContactRequestStatus enum in contact_request.py
- [X] T003 Create ContactRequest model
- [X] T004 Export model in backend/app/models/__init__.py

**Checkpoint**: ContactRequest entity exists and migrated. ✓

---

## Phase 2: Contact Service

- [X] T005 Create contact_service.py with `create_request(requester_id, project_id)` function
- [X] T006 Implement `get_existing_request(requester_id, project_id)` for duplicate check
- [X] T007 Implement `get_pending_requests_for_student(student_user_id)`
- [X] T008 Implement `approve_request(request_id)` with status update
- [X] T009 Implement `reject_request(request_id)` with status update
- [X] T010 Implement `get_student_for_project(project_id)` helper

**Checkpoint**: Contact request logic works. ✓

---

## Phase 3: Bot Handlers

- [X] T011 Create contact.py handler with `contact_request_callback`
- [X] T012 Implement role check (guest/business/expert only)
- [X] T013 Implement duplicate request check
- [X] T014 Send notification to student with approve/reject buttons
- [X] T015 Implement `contact_approve_callback` with contact exchange
- [X] T016 Implement `contact_reject_callback` with requester notification
- [X] T017 Register handlers in app.py

**Checkpoint**: Contact request flow works end-to-end. ✓

---

## Phase 4: Integration

- [X] T018 Add "Связаться с автором" button to project cards in recommendations
- [X] T019 Add button to Q&A project display
- [X] T020 Handle case when student has no username (use telegram_contact)

**Checkpoint**: Button appears in all project displays. ✓

---

## Phase 5: Polish

- [X] T021 Handle edge cases (student not found, requester no username)
- [X] T022 Add logging for audit trail
- [X] T023 Update tasks.md marking completed

---

## Dependencies & Execution Order

- Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5

**STATUS: COMPLETE** ✅
