# Implementation Plan: Contact Requests (EPIC-010)

**Version:** 1.0
**Date:** 2026-02-03
**Spec:** [spec.md](./spec.md)

---

## Tech Stack

| Component | Technology | Notes |
|-----------|------------|-------|
| Backend | Python 3.12+ / FastAPI | Existing stack |
| Bot | python-telegram-bot 21.x | Existing |
| ORM | SQLAlchemy 2.0 async | Existing |
| Database | PostgreSQL 16 | Existing |

---

## Architecture

### Component Diagram

```
┌───────────────────────────────────────────────────────────┐
│                     Telegram Bot                          │
│  ┌─────────────────┐  ┌─────────────────────────────────┐│
│  │  contact:req:id │  │  contact:approve / contact:reject ││
│  │  (requester)    │  │  (student)                       ││
│  └────────┬────────┘  └────────────────┬────────────────┘│
│           │                            │                  │
└───────────┼────────────────────────────┼──────────────────┘
            │                            │
            ▼                            ▼
┌───────────────────────────────────────────────────────────┐
│                  contact_service.py                       │
│  ┌───────────────────┐  ┌─────────────────────────────┐  │
│  │ create_request    │  │ approve_request             │  │
│  │ get_pending       │  │ reject_request              │  │
│  │ get_existing      │  │ send_contact_exchange       │  │
│  └───────────────────┘  └─────────────────────────────┘  │
│                                                           │
└───────────────────────────────────────────────────────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │ contact_request │
                  │    (model)      │
                  └─────────────────┘
```

---

## File Structure

```
backend/
├── alembic/versions/
│   └── 010_contact_request.py          # Migration
├── app/
│   ├── models/
│   │   └── contact_request.py          # ContactRequest model
│   ├── services/
│   │   └── contact_service.py          # Contact request logic
│   └── bot/handlers/
│       └── contact.py                  # Contact request handlers
```

---

## Database Changes

### New Table: contact_requests

```sql
CREATE TABLE contact_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    requester_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    student_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    requester_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    responded_at TIMESTAMP WITH TIME ZONE,
    UNIQUE(requester_id, project_id)
);

CREATE INDEX ix_contact_requests_student ON contact_requests(student_user_id, status);
CREATE INDEX ix_contact_requests_requester ON contact_requests(requester_id);
```

### Request Status Enum

```python
class ContactRequestStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
```

---

## Bot Handlers

### Callback: contact:req:{project_id}
- Check user is guest/business/expert (not organizer or author)
- Check no existing pending/approved request
- Create request with status=pending
- Send notification to student
- Reply to requester: "Запрос отправлен"

### Callback: contact:approve:{request_id}
- Verify sender is the student
- Update status → approved
- Send both parties each other's Telegram contact
- Reply: "Контакт передан"

### Callback: contact:reject:{request_id}
- Verify sender is the student
- Update status → rejected
- Notify requester: "Автор пока не готов"
- Reply to student: "Отклонено"

---

## Integration Points

### Project Card (recommendations, Q&A)
Add button "📞 Связаться с автором" with callback_data="contact:req:{project_id}"

### Student Notification
```
📩 Запрос на контакт

[Имя] ([роль]) хочет связаться с вами по проекту "[название]".

[Разрешаю] [Не сейчас]
```

### Contact Exchange Messages
To student: "✅ Контакт передан. Telegram: @requester_username"
To requester: "✅ Автор согласен! Telegram автора: @student_username"

---

## Error Handling

| Error | Action |
|-------|--------|
| Student not found | Log warning, show "Автор недоступен" |
| Request already exists | Show current status |
| Student has no username | Fallback to telegram_contact from project |
| Requester has no username | Prompt to set username in Telegram settings |

---

## Testing Strategy

- Unit tests for contact_service
- Integration test: full request → approve flow
- Test rejection flow
- Test duplicate request prevention
