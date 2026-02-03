# Research: DD Reminders Polish (EPIC-007b)

**Date**: 2026-02-03
**Parent**: EPIC-007 research.md

## R1: Message Truncation Strategy

**Decision**: Truncate project list with "...и ещё N проектов" suffix

**Rationale**:
- Telegram limit: 4096 bytes (UTF-8, so ~4096 chars for Cyrillic)
- Safe threshold: 4000 chars (buffer for emoji, formatting)
- User sees most relevant projects first (already sorted by relevance)
- Suffix indicates more content exists without confusing user

**Alternatives Considered**:
1. Split into multiple messages — rejected: breaks UX, complicates delivery tracking
2. Send link to web page — rejected: violates Telegram-First principle
3. Send only count, no projects — rejected: loses personalization value

**Implementation**:
```python
def truncate_message(text: str, max_len: int = 4000) -> str:
    if len(text) <= max_len:
        return text
    # Find last complete project entry before limit
    # Add "...и ещё N проектов" suffix
```

---

## R2: Interrupted Batch Detection

**Decision**: Check for `in_progress` status at `/remind` command start

**Rationale**:
- Simple single query: `WHERE status = 'in_progress' ORDER BY started_at DESC LIMIT 1`
- Shows only newest interrupted batch (per clarification)
- Gives organizer control: resume or start fresh

**Alternatives Considered**:
1. Auto-resume on bot restart — rejected: violates Human-Approved principle
2. Background worker auto-cleanup — rejected: adds complexity, hides state
3. Show all interrupted batches — rejected: confusing UX for rare scenario

**Implementation**:
```python
async def get_interrupted_batch(session, event_id) -> ReminderBatch | None:
    return await session.execute(
        select(ReminderBatch)
        .where(ReminderBatch.event_id == event_id)
        .where(ReminderBatch.status == ReminderBatchStatus.IN_PROGRESS)
        .order_by(ReminderBatch.started_at.desc())
        .limit(1)
    ).scalars().first()
```

---

## R3: Batch Resume Logic

**Decision**: Skip notifications with status `sent`, continue from where stopped

**Rationale**:
- `notifications` table tracks individual delivery status
- Resume = iterate recipients WHERE status != 'sent'
- No duplicate messages guaranteed by status check

**Alternatives Considered**:
1. Re-send all — rejected: duplicate spam, bad UX
2. Track last processed ID — rejected: more state to manage, fragile
3. Mark batch as failed, require full restart — rejected: loses progress

**Implementation**:
```python
async def resume_batch(session, batch, bot):
    # Get recipients not yet sent
    pending = await session.execute(
        select(Notification)
        .where(Notification.batch_id == batch.id)
        .where(Notification.status != NotificationStatus.SENT)
    )
    # Continue sending from pending list
```

---

## R4: E2E Validation Approach

**Decision**: Manual validation using quickstart.md scenarios

**Rationale**:
- Demo deadline: automated E2E tests are time-expensive
- 10 scenarios already documented in quickstart.md
- Manual execution ensures full flow coverage
- Can be automated in Release 1.1

**Alternatives Considered**:
1. Full pytest E2E suite — rejected: time constraint
2. Skip validation — rejected: risky for demo
3. Partial automation — rejected: inconsistent coverage

---

## Dependencies

| Dependency | Version | Purpose |
|------------|---------|---------|
| python-telegram-bot | 21.x | Bot API, already in EPIC-007 |
| SQLAlchemy | 2.0 | Async queries, already in EPIC-007 |

No new dependencies required.
