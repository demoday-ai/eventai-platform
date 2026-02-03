# Tasks: Guest Follow-up (EPIC-014)

**Version:** 1.0
**Date:** 2026-02-03

## Phase 1: Database & Model

- [X] Create FollowupPackage model (backend/app/models/followup_package.py)
- [X] Create Alembic migration (backend/alembic/versions/014_followup_package.py)
- [X] Export model in __init__.py

## Phase 2: Service Layer

- [X] Create followup_service.py with functions:
  - get_guest_recommendations()
  - get_approved_contacts()
  - generate_package_content()
  - get_or_create_package()
  - mark_package_sent()
  - format_package_message()
  - get_guests_without_package()

## Phase 3: Bot Handlers

- [X] Create followup.py handlers:
  - /followup command
  - refresh_callback
- [X] Register handlers in app.py

## Phase 4: Testing

- [ ] Test /followup with guest profile
- [ ] Verify package generation
- [ ] Test contact inclusion (approved only)
- [ ] Test refresh functionality
