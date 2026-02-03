# Research: Напоминания перед Demo Day (EPIC-007)

**Date**: 2026-02-03 | **Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

## Existing Reminder Infrastructure Analysis

### EPIC-003: Student Reminders
- **Location**: `participation_service.py`
- **Trigger**: DD-5 days (`send_reminders`)
- **Target**: Students with `status=SENT` (not acknowledged)
- **Tracking**: `reminder_sent_at` field on `ParticipationRequest`
- **Escalation**: DD-2 days → organizers (`escalate_to_organizers`)

### EPIC-004: Expert Reminders
- **Location**: `invite_service.py`
- **Trigger**: 3 days after invite viewed (`check_and_send_reminders`)
- **Target**: Experts with `status=invited`, `invite_viewed_at > 3 days`
- **Tracking**: `reminder_count`, `last_reminder_at` on `ExpertRoomAssignment`
- **Limit**: Max 4 reminders per expert

### Key Observations
1. Existing reminders are **threshold-based** (days since action), not **event-relative** (DD-1d, DD-1h)
2. Different tracking mechanisms per role — no unified `Notification` entity
3. Rate limiting pattern: `asyncio.sleep(0.04)` = ~25 msg/sec (safe under 30 msg/sec limit)
4. No existing `/remind` command — need to create from scratch

## Technical Decisions

### Decision 1: New Tables vs Extend Existing

**Options**:
- A) Add `dd_reminder_sent_at` fields to existing models
- B) Create new `reminder_batches` + `notifications` tables

**Decision**: Option B — New tables

**Rationale**:
- Clean separation of DD-relative reminders from existing threshold-based reminders
- `ReminderBatch` enables tracking of batch operations (preview, confirm, report)
- `Notification` provides unified audit trail across all roles
- Aligns with ER diagram spec (notifications table planned but not implemented)
- Enables future multi-channel expansion (email, SMS)

### Decision 2: Message Personalization

**Strategy**: Template-based with role-specific content

| Role | Day-Before Message | Hour-Before Message |
|------|-------------------|---------------------|
| Student | Зал, проект, «подтвердите если не сделали» | «Через час — твоё выступление! Зал X» |
| Expert | Зал, N проектов | «Через час — Зал X. Первый проект: Y» |
| Guest | Топ-5 проектов из программы | «DD начинается! Рекомендуем Зал X» |
| Business | Топ-5 проектов из подборки | «DD начинается! Рекомендуем Зал X» |

### Decision 3: Recipient Selection Logic

**Students**:
- Source: `ParticipationRequest` with `room_project_id` set
- Filter: `user_id IS NOT NULL` (has Telegram)
- Include unacknowledged with reminder note

**Experts**:
- Source: `ExpertRoomAssignment` with `status IN ('confirmed', 'invited', 'proposed', 'approved', 'invite_ready')`
- Filter: `status != 'declined'`
- Need: `telegram_user_id` from `Expert.bot_started` users (store chat_id)

**Guests/Business**:
- Source: `User` with guest profiling data
- Filter: `guest_subtype IS NOT NULL` OR has `BusinessProfile`
- Program: From `GuestProgram` (EPIC-005) or empty with prompt

### Decision 4: Telegram User ID Storage

**Problem**: Experts have `telegram_username` but not `telegram_user_id` (chat_id needed for messaging)

**Solution**:
- Add `telegram_chat_id` field to `Expert` model (set when bot_started)
- For new EPIC-007: require `telegram_user_id` — skip users without it, report in summary

### Decision 5: Command Flow

```
/remind → Preview → Confirm → Send → Report
```

**Preview Response**:
```
📢 Напоминания за [день/час]

Студенты: 280 (12 без Telegram)
Эксперты: 45 (3 отклонили)
Гости: 35 (8 без программы)
Бизнес: 12

Итого: 372 получателя

[Отправить] [Отмена]
```

**Report Response**:
```
✅ Рассылка завершена

Отправлено: 365
Ошибки: 7 (бот заблокирован)
Пропущено: 12 (нет Telegram)

Время: 2 мин 34 сек
```

### Decision 6: Duplicate Prevention

**Mechanism**:
- Check `ReminderBatch` for same `event_id`, `reminder_type`, within last 24 hours
- If found: show warning «Напоминания уже отправлены X минут назад. Отправить повторно?»
- Store batch result for audit trail

## Data Model Decisions

### ReminderBatch

```python
class ReminderBatch(Base):
    id: UUID
    event_id: UUID (FK)
    reminder_type: Enum('day_before', 'hour_before')
    initiated_by: str  # telegram_user_id of organizer

    # Counts
    total_recipients: int
    sent_count: int
    failed_count: int
    skipped_count: int  # no telegram

    # Timing
    started_at: datetime
    completed_at: datetime | None

    # Status
    status: Enum('preview', 'in_progress', 'completed', 'cancelled')
```

### Notification

```python
class Notification(Base):
    id: UUID
    batch_id: UUID (FK)
    user_id: UUID (FK, nullable)  # for guests/business
    expert_id: UUID (FK, nullable)  # for experts
    participation_id: UUID (FK, nullable)  # for students

    recipient_type: Enum('student', 'expert', 'guest', 'business')
    telegram_user_id: str

    status: Enum('pending', 'sent', 'failed')
    error_message: str | None
    sent_at: datetime | None
```

## API Design

### Bot Commands

| Command | Access | Description |
|---------|--------|-------------|
| `/remind` | Organizer | Start reminder flow |
| `/remind day` | Organizer | Day-before reminders |
| `/remind hour` | Organizer | Hour-before reminders |

### Callbacks

| Pattern | Action |
|---------|--------|
| `rem:preview:day` | Show day-before preview |
| `rem:preview:hour` | Show hour-before preview |
| `rem:send:{batch_id[:8]}` | Confirm and send |
| `rem:cancel` | Cancel reminder flow |
| `rem:resend:{batch_id[:8]}` | Resend despite duplicate warning |

### REST API (minimal)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `GET /api/v1/reminders/batches` | GET | List reminder batches for event |
| `GET /api/v1/reminders/batches/{id}` | GET | Batch details with notifications |

## Edge Cases & Handling

| Case | Handling |
|------|----------|
| No telegram_user_id | Skip, count in `skipped_count`, include in report |
| Bot blocked by user | Catch exception, mark `failed`, continue |
| Rate limit (30 msg/sec) | 0.04s delay between sends |
| Batch interrupted | Save progress, resume on retry |
| Duplicate send attempt | Warn organizer, require explicit confirmation |
| No event in 2 days | Show "Нет события в ближайшие дни" |
| Expert declined | Skip, don't count in recipients |
| Guest without program | Send generic reminder with profiling prompt |

## Performance Estimates

| Metric | Target | Implementation |
|--------|--------|----------------|
| 400 recipients | <3 min | 0.04s × 400 = 16s send time + overhead |
| Message formatting | <1s | In-memory template formatting |
| DB queries | <5s | Batch loading with eager joins |
| Total batch time | <2.5 min | Well under 3 min target |

## Dependencies

| Dependency | Purpose | Status |
|------------|---------|--------|
| EPIC-003 | Student participation data | ✅ Exists |
| EPIC-004 | Expert assignment data | ✅ Exists |
| EPIC-005 | Guest program data | ✅ Exists |
| EPIC-006 | Coverage data (for expert room info) | ✅ Exists |
