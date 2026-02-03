# Quickstart: Напоминания перед Demo Day (EPIC-007)

**Date**: 2026-02-03 | **Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

## Prerequisites

1. Bot running with approved clustering (EPIC-002)
2. Students with slots from `/broadcast` (EPIC-003)
3. Experts with assignments (EPIC-004)
4. Optional: Guests/Business with profiles (EPIC-005)
5. Event with `start_date` set to tomorrow or today

## Test Scenarios

### Scenario 1: Day-Before Reminder — Basic Flow

**Setup**:
- Event `start_date` = tomorrow
- At least 1 student with `ParticipationRequest` + `user_id`
- At least 1 expert with `status=confirmed` + `telegram_chat_id`

**Steps**:
1. Organizer sends `/remind`
2. Bot shows type selection: `[За день] [За час]`
3. Organizer clicks `За день`
4. Bot shows preview:
   ```
   📢 Напоминания за день до DD

   Студенты: N (M без Telegram)
   Эксперты: X (Y отклонили)
   Гости: G
   Бизнес: B

   Итого: Z получателей

   [Отправить] [Отмена]
   ```
5. Organizer clicks `Отправить`
6. Bot sends messages with 0.04s delay
7. Bot shows report:
   ```
   ✅ Рассылка завершена

   Отправлено: A
   Ошибки: B
   Пропущено: C

   Время: X мин Y сек
   ```

**Expected**:
- Student receives: «Завтра ты выступаешь! Зал «X», проект «Y»»
- Expert receives: «Завтра, Зал «X». N проектов ждут вашей оценки»
- `ReminderBatch` created with `status=completed`
- `Notification` records for each recipient

---

### Scenario 2: Hour-Before Reminder

**Setup**:
- Event `start_date` = today, start time in ~1 hour
- Same recipients as Scenario 1

**Steps**:
1. `/remind` → `За час`
2. Preview → `Отправить`

**Expected**:
- Student: «Через час — твоё выступление! Зал «X»»
- Expert: «Через час — Зал «X». Первый проект: «Y»»
- Guest: «DD начинается через час! Рекомендуем начать с Зала «X»»

---

### Scenario 3: Duplicate Warning

**Setup**:
- Run Scenario 1 (day-before reminders sent)
- Wait 5 minutes

**Steps**:
1. Organizer sends `/remind` → `За день` again

**Expected**:
- Bot shows warning:
  ```
  ⚠️ Напоминания «за день» уже отправлены 5 минут назад.

  Отправить повторно?

  [Да, отправить] [Отмена]
  ```

---

### Scenario 4: Non-Organizer Access

**Setup**:
- Regular user (not in `organizer_ids`)

**Steps**:
1. User sends `/remind`

**Expected**:
- Bot responds: «Команда доступна только организаторам»

---

### Scenario 5: No Event

**Setup**:
- No event with `start_date` within 2 days

**Steps**:
1. Organizer sends `/remind`

**Expected**:
- Bot responds: «Нет события в ближайшие дни»

---

### Scenario 6: Student Without Acknowledgment

**Setup**:
- Student with `ParticipationRequest.status = SENT` (not acknowledged)

**Steps**:
1. Run day-before reminders

**Expected**:
- Student receives reminder with note:
  ```
  Завтра ты выступаешь! Зал «X», проект «Y»

  ⚠️ Пожалуйста, подтвердите участие.

  [Ознакомлен]
  ```

---

### Scenario 7: Expert Declined

**Setup**:
- Expert with `ExpertRoomAssignment.status = declined`

**Steps**:
1. Run day-before reminders

**Expected**:
- Declined expert NOT in recipient list
- Preview shows: «Эксперты: N (1 отклонил)»

---

### Scenario 8: Guest Without Program

**Setup**:
- Guest user with `guest_subtype` set but no saved program

**Steps**:
1. Run day-before reminders

**Expected**:
- Guest receives:
  ```
  Завтра Demo Day!

  Пройдите профилирование, чтобы получить персональную программу.

  [Начать профилирование]
  ```

---

### Scenario 9: Rate Limit Compliance

**Setup**:
- 100+ recipients

**Steps**:
1. Run reminders, monitor send rate

**Expected**:
- Messages sent at ~25/sec (0.04s delay)
- No Telegram rate limit errors
- Batch completes within expected time

---

### Scenario 10: Interrupted Batch

**Setup**:
- Start sending, simulate interruption (bot restart)

**Steps**:
1. `/remind` → `За день` → `Отправить`
2. Restart bot mid-send
3. `/remind` → `За день` again

**Expected**:
- Bot detects incomplete batch
- Shows: «Предыдущая рассылка не завершена. Продолжить?»
- On confirm: resumes from last successful send

---

## Message Templates

### Student — Day Before

```
📅 Завтра ты выступаешь!

Проект: {project.title}
Зал: {room.name}
Дата: {event.start_date:%d.%m.%Y}

{if not acknowledged}
⚠️ Пожалуйста, подтвердите участие.
[Ознакомлен]
{/if}
```

### Expert — Day Before

```
📅 Завтра Demo Day!

Зал: {room.name}
Проектов: {project_count}

Ждём вас для оценки проектов!
```

### Guest — Day Before (with program)

```
📅 Завтра Demo Day!

Ваша программа:
• {program[0].project_title} ({program[0].room_name})
• {program[1].project_title} ({program[1].room_name})
• {program[2].project_title} ({program[2].room_name})
{if len(program) > 3}... ещё {len(program) - 3}{/if}

До встречи!
```

### Student — Hour Before

```
⏰ Через час — твоё выступление!

Зал: {room.name}
Проект: {project.title}

Удачи! 🎯
```

### Expert — Hour Before

```
⏰ Через час — начало!

Зал: {room.name}
Первый проект: {first_project.title}

Ждём вас!
```

### Guest — Hour Before

```
⏰ DD начинается через час!

Рекомендуем начать с Зала «{recommended_room.name}»

{program_summary}
```

## Validation Checklist

- [ ] `/remind` command registered and responds
- [ ] Type selection keyboard works
- [ ] Preview shows correct counts
- [ ] Send button triggers batch
- [ ] Messages delivered to all role types
- [ ] Rate limiting working (no 429 errors)
- [ ] Failed deliveries logged and counted
- [ ] Report shows accurate stats
- [ ] Duplicate warning appears on resend
- [ ] Non-organizer blocked
- [ ] No event handled gracefully
- [ ] Unacknowledged students get reminder note
- [ ] Declined experts excluded
- [ ] Guests without program get prompt
- [ ] Batch records created in DB
- [ ] Notification records created in DB
