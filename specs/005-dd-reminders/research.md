# Research: DD Reminders & Timing Shift Notifications (EPIC-005)

**Date**: 2026-02-02 | **Status**: Complete

## R1: Schedule Slot Auto-Generation Strategy

**Decision**: Auto-generate equal-length slots (15 min per project) within each room based on event start/end times and the approved clustering's project-room assignments. Each project gets exactly one slot. Slots ordered by `room_projects.display_order` (if set) or alphabetical by project title.

**Rationale**: Demo Day uses a 15-minute format per project (presentation + Q&A), consistent across all rooms. The event has fixed hours (e.g., 10:30-19:30 Day 1, 14:00-19:30 Day 2). Auto-generation from approved clustering provides instant schedule with zero manual effort. Organizer can adjust individual slots after generation.

**Slot timing calculation**:
```
For each room in approved_clustering.rooms:
    event_day = determine_day(room)  # Day 1 or Day 2 based on room config
    start = event_day.start_time     # e.g. 10:30 MSK
    slot_duration = 15 minutes
    for i, project in enumerate(room.projects):
        slot.start_time = start + (i * slot_duration)
        slot.end_time = slot.start_time + slot_duration
```

**Alternatives considered**:
- **Variable slot durations** (configurable per project): Rejected — all DD projects use same 15-min format; adds complexity with no benefit for MVP.
- **Organizer enters all slots manually**: Rejected — ~330 manual entries is error-prone and time-consuming. Auto-generation with manual adjustments is faster.
- **Import from CSV/spreadsheet**: Rejected for MVP — auto-generation is simpler. CSV import can be added in Release 1.1 if needed.

## R2: Notification Delivery Architecture

**Decision**: Use existing APScheduler with more granular job scheduling. Three job types:
1. **Eve-of-DD job**: Cron trigger at 18:00 MSK, day before each event day
2. **Pre-slot checker**: Interval trigger every 5 minutes on DD day (active only between event start - 1h and event end)
3. **Timing shift**: Event-driven (triggered synchronously when schedule changes are saved via service layer)

**Rationale**: APScheduler already runs in the app (EPIC-004 uses IntervalTrigger(hours=12)). Adding CronTrigger for eve-of-DD and tighter IntervalTrigger for pre-slot is natural. Timing shifts don't need a scheduler — they fire immediately when the organizer saves a change.

**Throttling**: Telegram allows 30 msg/sec to different users. For ~400 participants, mass send takes ~14 seconds. Implementation: asyncio.Semaphore(25) to stay safely under limit, with asyncio.sleep(0.05) between sends.

**Alternatives considered**:
- **Celery + Redis**: Rejected — adds 2 dependencies (Redis, Celery) for a problem APScheduler already solves. Team has 3 people + 5-day timeline.
- **External cron (systemd timer)**: Rejected — requires system-level configuration, harder to deploy, no integration with app state.
- **Telegram Bot API webhooks for delivery confirmation**: Not available — Bot API doesn't provide read receipts. We track "sent" (no exception) vs "failed" (API error).

## R3: Notification Batching for Rapid Schedule Changes

**Decision**: 5-minute debounce window per participant. When a schedule change affects a participant, enqueue a pending notification. A background task checks every 60 seconds for pending notifications older than 5 minutes, batches all pending changes for the same participant into one message, and sends.

**Rationale**: Organizer may rapidly move multiple projects (e.g., rebalancing a room). Sending one notification per change would spam participants. A 5-minute window allows batching while staying within the 2-minute SLA for isolated changes (the 5-min window only accumulates if more changes keep arriving).

**Batch message format**:
```
📋 Изменения в расписании:

• Проект "X": 14:00 → 16:00, Зал 3
• Проект "Y": перенесён в Зал 2, 15:00
• Проект "Z": отменён

Ваша обновлённая программа: [inline button]
```

**Alternatives considered**:
- **No batching (instant send)**: Rejected — organizer moving 5 projects in 2 minutes = 5 separate messages per affected participant.
- **Longer window (15 min)**: Rejected — too slow for single changes; spec requires < 2 min for isolated changes.
- **Queue-based (Redis pub/sub)**: Rejected — overkill; in-memory debounce with DB-backed pending notifications is sufficient at this scale.

## R4: Pre-Slot Reminder Deduplication

**Decision**: Track sent pre-slot reminders in the `notifications` table with a composite key of (user_id, schedule_slot_id, type='pre_slot'). Before sending, check if a notification with this key already exists with status != 'failed'. Additionally enforce 30-minute cooldown per participant using `MAX(sent_at) WHERE user_id = ? AND type = 'pre_slot'`.

**Rationale**: The 5-minute checker runs repeatedly throughout DD day. Without dedup, a participant could receive 12 reminders for the same slot (5-min interval × 60-min window). DB-level tracking is reliable across app restarts.

**Alternatives considered**:
- **In-memory set of sent reminders**: Rejected — lost on app restart; not reliable for a multi-hour DD event.
- **Redis-based dedup**: Rejected — adds dependency for a simple lookup that PostgreSQL handles well.

## R5: Eve-of-DD Organizer Preview & Cancel

**Decision**: At 17:00 MSK (1 hour before scheduled send), the system sends a preview message to the organizer showing: number of recipients by role, a sample message for each role, and inline buttons "Подтвердить отправку" / "Отменить отправку". If organizer confirms or doesn't respond by 18:00, the system proceeds with sending. If organizer cancels, no reminders are sent (can be re-triggered manually).

**Rationale**: Hybrid approach from clarification (auto-send with cancel window). The organizer gets visibility without being a blocker. Preview at 17:00 gives 1 hour to review. Default behavior is to send (not block), which is safer — a forgotten preview shouldn't block reminders.

**Flow**:
```
17:00 MSK (T-1h):
  → Send preview to all organizer_telegram_ids
  → Show: "В 18:00 будет отправлено N напоминаний (X студентов, Y экспертов, Z гостей)"
  → Inline buttons: [✅ Подтвердить] [❌ Отменить]

18:00 MSK (T-0):
  → If cancelled: skip, log "cancelled by organizer"
  → If confirmed or no response: send reminders
```

**Alternatives considered**:
- **Organizer must explicitly confirm**: Rejected — if organizer forgets, no reminders go out. Worse outcome than sending.
- **No preview**: Rejected — clarification explicitly chose hybrid mode.

## R6: Multi-Day Event Handling

**Decision**: Event has `start_date` and `end_date`. Schedule slots have datetime (not just time). The eve-of-DD reminder job checks: for each day in the event range, send reminders at 18:00 the previous day. Pre-slot reminders run on each event day independently.

**Rationale**: Demo Day 2026 spans 2 days (Feb 6-7). Day 1 reminders go out Feb 5 at 18:00, Day 2 reminders go out Feb 6 at 18:00. Pre-slot reminders run on both Feb 6 and Feb 7. Participants only receive reminders for days where they have scheduled items.

**Edge case**: A participant with items on both days gets two eve-of-DD reminders (one per day), each listing only that day's items.

**Alternatives considered**:
- **Single reminder for entire event**: Rejected — Day 2 info sent on Day 0 (Feb 5) is too early and may be stale by Day 2.
- **Hardcoded 2-day logic**: Rejected — using event date range is generic and handles any duration.

## R7: Escalation Reuse for Undeliverable Notifications

**Decision**: Extend existing `escalations` table with new types: `notification_undeliverable`, `reminder_send_failed`. Reuse the existing escalation dashboard in EPIC-004 organizer flow.

**Rationale**: EPIC-004 already has escalation infrastructure (model, service, bot handler). Adding new types is trivial. Organizer already knows how to check escalations via `/escalations` command.

**New escalation types**:
- `notification_undeliverable` — participant never started bot, can't receive messages
- `reminder_send_failed` — Telegram API returned error after 3 retries

**Schema change**: Escalation model already uses `type: str` (not enum), so no migration needed for new types. The `expert_id` FK is nullable for non-expert escalations; we'll also reference user_id directly.

**Alternatives considered**:
- **Separate notification_failures table**: Rejected — duplicates escalation logic; organizer would need to check two places.
- **Silent failure logging (no organizer alert)**: Rejected — spec requires organizer visibility into delivery failures.

## R8: Guest/Business Personal Program Dependency

**Decision**: This feature reads personal programs from EPIC-005 (guest profiling) and EPIC-006 (business profiling) data. If those features aren't implemented yet, reminders for guests/business degrade gracefully: send a generic "Завтра Demo Day! Полное расписание: [link]" without personalized program.

**Rationale**: EPIC-005/006 may not be implemented before this feature. Reminders for students and experts don't depend on profiling — they use room/slot assignments. Guest reminders can work with or without a personal program.

**Graceful degradation**:
- With personal program: "Вот ваша программа: [list of projects]"
- Without personal program: "Завтра Demo Day! Используйте /program чтобы получить персональную подборку."

**Alternatives considered**:
- **Hard dependency on EPIC-005/006**: Rejected — blocks reminder delivery for guests until profiling is built. Students and experts are the primary audience anyway.
