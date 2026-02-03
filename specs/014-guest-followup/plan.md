# Implementation Plan: Guest Follow-up (EPIC-014)

**Version:** 1.0
**Date:** 2026-02-03

## File Structure

```
backend/
├── alembic/versions/
│   └── 014_followup_package.py
├── app/
│   ├── models/
│   │   └── followup_package.py
│   ├── services/
│   │   └── followup_service.py
│   └── bot/handlers/
│       └── followup.py
```

## Bot Flow

1. After DD ends (24h) → auto-generate packages for all guests
2. /followup command → manual request
3. Package includes:
   - Projects from recommendations
   - Guest's ratings/comments
   - Contact info (if approved)
   - Template message for outreach

## Commands

- /followup — get personal follow-up package

## Integration Points

- EPIC-005: GuestProfile for interests
- EPIC-009: QA suggestions for context
- EPIC-010: ContactRequest for approved contacts
- EPIC-012: FeedbackComment for guest feedback
