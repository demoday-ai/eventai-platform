# Feature Specification: DD Reminders & Timing Shift Notifications

**Feature Branch**: `005-dd-reminders`
**Created**: 2026-02-02
**Status**: Draft
**Input**: User description: "from file docs/02-specification/02-user-story-map.md — EPIC-007 (Напоминалки) + EPIC-007b (Уведомления о сдвигах тайминга)"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Eve-of-DD Reminders for All Participants (Priority: P1)

The day before Demo Day, the system automatically sends personalized reminder messages to all confirmed participants via the Telegram bot. Each role receives a tailored message:

- **Students** receive: "Завтра Demo Day! Ты выступаешь в [Зал X], время [Y]. Удачи!"
- **Experts** receive: "Завтра Demo Day! Ваша комната: [Зал X], время [Y]. Вот проекты, которые вы будете оценивать: [список]"
- **Guests and Business partners** receive: "Завтра Demo Day! Вот ваша персональная программа: [список проектов с залами и временем]"

The goal is to reduce no-shows and ensure every participant knows exactly where and when they need to be.

**Why this priority**: RICE score 760 — the highest priority feature in the backlog. Reminders directly reduce no-shows (a key organizational pain point) and require no user interaction, only system automation.

**Independent Test**: Can be tested by scheduling a reminder for a test event and verifying that each role receives the correct personalized message with accurate schedule details.

**Acceptance Scenarios**:

1. **Given** a confirmed student with an assigned room and time slot, **When** the system runs the eve-of-DD reminder job, **Then** the student receives a Telegram message with their exact room name, date, and time slot.
2. **Given** a confirmed expert with an assigned room, **When** the system runs the eve-of-DD reminder job, **Then** the expert receives a Telegram message listing their room, time, and the projects they will evaluate.
3. **Given** a profiled guest with a personal program, **When** the system runs the eve-of-DD reminder job, **Then** the guest receives a Telegram message with their curated project list including rooms and times.
4. **Given** a profiled business partner with a personal program, **When** the system runs the eve-of-DD reminder job, **Then** the business partner receives a Telegram message with their curated project list including rooms and times.
5. **Given** a user who has not started the bot (never sent /start), **When** the system attempts to send a reminder, **Then** the system logs a delivery failure and creates an escalation for the organizer.

---

### User Story 2 - Pre-Slot Reminders (Priority: P2)

One hour before a participant's relevant time slot, the system sends a short "heads up" reminder:

- **Students**: "Через час — твоё выступление в [Зал X]!"
- **Experts**: "Через час — начало оценки в [Зал X]!"
- **Guests/Business**: "Через час — [Проект Y] в [Зал X], который вы хотели посмотреть!" (the single highest-relevance project from their personal program starting in the next hour)

These reminders are sent only on the day of Demo Day itself and are timed relative to each participant's personal schedule.

**Why this priority**: Pre-slot reminders catch participants who are already at the venue but may lose track of time or rooms. They are a natural extension of eve-of-DD reminders but require time-aware scheduling.

**Independent Test**: Can be tested by setting a time slot 1 hour in the future, then verifying the reminder fires at the correct time with the correct content.

**Acceptance Scenarios**:

1. **Given** a student whose presentation starts at 14:00, **When** the current time reaches 13:00 on DD day, **Then** the student receives a Telegram reminder about their upcoming slot.
2. **Given** a guest whose first program item starts at 11:00, **When** the current time reaches 10:00 on DD day, **Then** the guest receives a reminder about the upcoming project.
3. **Given** a participant with back-to-back items (no 1-hour gap), **When** the system schedules pre-slot reminders, **Then** the system does not send overlapping reminders — it sends at most one reminder per 30-minute window.
4. **Given** a participant who has already received a pre-slot reminder for a specific slot, **When** the reminder job runs again, **Then** the system does not send a duplicate reminder.

---

### User Story 3 - Timing Shift Notifications (Priority: P2)

When an organizer changes the schedule of a project (e.g., moves it to a different time or room), the system automatically notifies all affected participants:

- Guests and business partners who have this project in their personal program receive: "Проект [X] перенесён: было [время1] → стало [время2], Зал [Y]"
- Students whose slot changed receive: "Твоё выступление перенесено: было [время1] → стало [время2], Зал [Y]"
- Experts assigned to the affected room receive a notification about the schedule change

This addresses a key pain point from interviews: a guest missed the most interesting project because the timing shifted and no one told them.

**Why this priority**: Validated by interview #4 (Nastya): "не успела посмотреть самый интересный, потому что съехал тайминг. Если бы я знала — ушла бы с менее интересного." Real-time notification is critical for participant satisfaction, but depends on schedule data infrastructure.

**Independent Test**: Can be tested by changing a project's time slot and verifying that all participants with that project in their schedule/program receive an immediate notification.

**Acceptance Scenarios**:

1. **Given** a guest has Project X in their personal program scheduled at 14:00, **When** an organizer moves Project X to 16:00, **Then** the guest immediately receives a Telegram notification with old and new time.
2. **Given** a student is assigned to present at 12:00 in Room 3, **When** an organizer changes their slot to 13:00 in Room 3, **Then** the student immediately receives a notification about the change.
3. **Given** an expert is assigned to Room 3 where a project schedule shifted, **When** the shift occurs, **Then** the expert receives a notification about the updated room schedule.
4. **Given** a project is moved and a participant has not started the bot, **When** the system tries to send a timing shift notification, **Then** the system logs the undeliverable notification and creates an escalation for the organizer.
5. **Given** an organizer makes multiple rapid schedule changes (within 5 minutes), **When** notifications are generated, **Then** the system batches them into a single message per participant to avoid spam.

---

### User Story 4 - Organizer Reminder Dashboard (Priority: P3)

The organizer can view the status of all reminders and notifications: how many were sent, how many failed to deliver, and which participants have not been reached. This gives the organizer visibility into communication coverage before and during Demo Day.

**Why this priority**: Provides organizers with control and transparency over the reminder system. Less urgent than the reminders themselves, but important for operational confidence.

**Independent Test**: Can be tested by sending reminders to a set of test participants and then checking the dashboard for accurate counts and delivery statuses.

**Acceptance Scenarios**:

1. **Given** the eve-of-DD reminders have been sent, **When** an organizer requests the reminder dashboard, **Then** they see a summary: total sent, delivered, failed, broken down by role (student/expert/guest/business).
2. **Given** some reminders failed to deliver (user never started bot), **When** an organizer views the dashboard, **Then** they see a list of unreachable participants with names and roles.
3. **Given** timing shift notifications have been sent, **When** an organizer views the dashboard, **Then** they see: (a) a summary count of timing shift notifications sent, and (b) can drill down via notification list filtered by type=timing_shift to see individual recipients and timestamps.

---

### Edge Cases

- What happens when a participant has no assigned room or time slot (e.g., a guest who completed profiling but the schedule is not yet approved)? The system skips the reminder and does not send an incomplete message.
- What happens when Demo Day spans multiple days (e.g., Day 1 and Day 2)? Reminders are sent the evening before each respective day, and pre-slot reminders fire on the correct day.
- What happens if the organizer changes a project's schedule after the eve-of-DD reminder was already sent? A timing shift notification is sent as a correction, referencing the original time from the reminder.
- What happens when a participant's personal program becomes empty due to all their projects being cancelled? The system sends a notification: "Все проекты из вашей программы были отменены. Обратитесь к организатору."
- What happens when the bot is temporarily unavailable during a scheduled reminder window? The system retries delivery up to 3 times with exponential backoff, then logs a failure.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST automatically send personalized eve-of-DD reminder messages to all confirmed participants (students, experts, guests, business partners) at the scheduled time the day before Demo Day, with built-in throttling to respect messaging rate limits.
- **FR-002**: System MUST tailor reminder content to each role: students see their presentation slot, experts see their room and project list, guests and business partners see their personal program.
- **FR-003**: System MUST send pre-slot reminders 1 hour before each participant's relevant time slot on the day of Demo Day. For guests and business partners, the reminder highlights the single highest-relevance project from their personal program starting in that window.
- **FR-004**: System MUST NOT send duplicate reminders for the same slot to the same participant.
- **FR-005**: System MUST NOT send more than one pre-slot reminder per participant within a 30-minute window.
- **FR-006**: System MUST immediately notify affected participants when a project's time slot or room is changed by an organizer.
- **FR-007**: Timing shift notifications MUST include both old and new time/room information.
- **FR-008**: System MUST batch multiple rapid schedule changes (within 5 minutes) into a single notification per participant.
- **FR-009**: System MUST log all sent notifications with delivery status (sent, delivered, failed).
- **FR-010**: System MUST create an escalation record for the organizer when a notification cannot be delivered (e.g., user never started the bot).
- **FR-011**: Organizers MUST be able to view a dashboard showing reminder delivery statistics by role and a list of unreachable participants.
- **FR-012**: System MUST support multi-day Demo Day events, sending reminders for the correct day.
- **FR-013**: System MUST retry failed notification deliveries up to 3 times before marking as permanently failed.
- **FR-014**: Timing shift notifications MUST be triggered automatically when an organizer modifies the schedule, without requiring a manual "send notification" action.
- **FR-015**: Organizers MUST be able to preview the list of pending eve-of-DD reminders and cancel the scheduled send up to 1 hour before the send time.
- **FR-016**: System MUST auto-generate schedule slots from event dates, room count, and project-room assignments, distributing projects into equal-length time blocks per room.
- **FR-017**: Organizers MUST be able to adjust auto-generated schedule slots (change time, move project between slots, cancel a slot) before and during Demo Day.

### Key Entities

- **Notification**: A record of a message sent (or attempted) to a participant. Key attributes: recipient (user), type (eve-of-DD reminder, pre-slot reminder, timing shift), content, scheduled time, sent time, delivery status, retry count.
- **Schedule Slot**: A time block within a Demo Day event representing when a project is presented in a specific room. Initially auto-generated from event dates, room count, and project assignments (equal-length blocks per room), then adjustable by the organizer. Key attributes: event, room, project, start time, end time, status (scheduled, cancelled, moved).
- **Schedule Change Log**: An audit trail entry recording when and how a schedule slot was modified. Key attributes: slot, old start time, old room, new start time, new room, changed by (organizer), change timestamp.

## Clarifications

### Session 2026-02-02

- Q: Should eve-of-DD reminders be fully automatic, organizer-triggered, or hybrid? → A: Hybrid — system auto-sends at scheduled time, but organizer can preview and cancel up to 1 hour before the scheduled send time.
- Q: What timezone should be used for all reminder scheduling? → A: Moscow time (UTC+3), since Demo Day is a physical event in Moscow.
- Q: How should schedule slots be created? → A: Auto-generated from event dates and room count (equal time blocks per room), then organizer adjusts as needed.
- Q: Should pre-slot reminders for guests/business show all upcoming projects or just one? → A: Only the top-ranked project by relevance score from the personal program.

## Assumptions

- All participant communication happens via Telegram bot messages. No email or SMS channel is used.
- The existing APScheduler infrastructure (already running 12-hour interval jobs) will be extended to support more granular scheduling (hourly or per-minute checks on DD day).
- Eve-of-DD reminders are sent at 18:00 Moscow time (UTC+3) the day before Demo Day (evening, so participants see it before bed or in the morning). All reminder and notification scheduling uses Moscow time.
- Pre-slot reminders fire exactly 1 hour before the slot; the system checks for upcoming slots every 5 minutes on DD day.
- The schedule is auto-generated from event dates and approved clustering (rooms + project assignments), then optionally adjusted by the organizer. The schedule must be finalized and approved before reminders can be sent. If the schedule is not yet approved, the system does not send reminders.
- Existing escalation patterns (from EPIC-004) are reused for undeliverable notifications.
- Guest and business partner "personal programs" are generated by EPIC-005/EPIC-006 and are available as stored data the reminder system can reference.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of confirmed participants with active bot sessions receive their eve-of-DD reminder within 1 hour of the scheduled send time.
- **SC-002**: Pre-slot reminders are delivered within 5 minutes of the 1-hour-before mark for each slot.
- **SC-003**: Timing shift notifications reach affected participants within 2 minutes of the schedule change being saved.
- **SC-004**: No participant receives duplicate reminders for the same event/slot.
- **SC-005**: The organizer dashboard accurately reflects delivery status for 100% of sent notifications.
- **SC-006**: Participant no-show rate decreases compared to events without reminders (target: reduce no-shows by at least 20%).
- **SC-007**: 0 participants miss a rescheduled project due to lack of notification (measured by post-DD survey).
