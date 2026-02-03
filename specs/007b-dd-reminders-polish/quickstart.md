# Quickstart: DD Reminders Polish (EPIC-007b)

**Prerequisite**: EPIC-007 fully implemented and working

## Test Scenarios

### Scenario 1: Message Truncation - Short Program

**Purpose**: Verify messages under limit are not truncated

1. Create guest with 5 projects in program
2. Run `/remind` → select "За день"
3. Confirm send
4. **Expected**: Guest receives message with all 5 projects listed

### Scenario 2: Message Truncation - Long Program

**Purpose**: Verify long messages are truncated correctly

1. Create guest with 25+ projects in program
2. Run `/remind` → select "За день"
3. Confirm send
4. **Expected**:
   - Guest receives message under 4096 chars
   - Message ends with "...и ещё N проектов" where N = remaining count
   - First ~10 projects are shown (most relevant)

### Scenario 3: Batch Recovery - Detection

**Purpose**: Verify interrupted batch is detected

1. Start a reminder batch
2. Stop the bot mid-send (Ctrl+C or kill process)
3. Restart bot
4. Run `/remind`
5. **Expected**:
   - Message: "Обнаружена прерванная рассылка от [time]"
   - Buttons: "Возобновить" / "Начать заново" / "Отмена"
   - Shows: sent/total progress

### Scenario 4: Batch Recovery - Resume

**Purpose**: Verify resume sends only to pending recipients

1. Complete Scenario 3 setup (interrupted batch)
2. Click "Возобновить"
3. **Expected**:
   - Only unsent recipients receive messages
   - Previously sent recipients do NOT receive duplicates
   - Final report shows combined totals

### Scenario 5: Batch Recovery - Start Fresh

**Purpose**: Verify fresh start cancels old batch

1. Complete Scenario 3 setup (interrupted batch)
2. Click "Начать заново"
3. **Expected**:
   - Old batch status → `cancelled`
   - New batch created
   - All recipients in new batch (clean slate)

### Scenario 6: Multiple Interrupted Batches

**Purpose**: Verify only newest is shown

1. Create first interrupted batch (stop mid-send)
2. Restart bot
3. Start second batch, interrupt again
4. Restart bot
5. Run `/remind`
6. **Expected**:
   - Only second (newest) batch shown for recovery
   - First batch remains `in_progress` (manual cleanup via REST API)

### Scenario 7: Edge - Empty Batch Recovery

**Purpose**: Verify completed batch is not shown for recovery

1. Complete a full batch (all sent)
2. Restart bot
3. Run `/remind`
4. **Expected**: Normal flow (type selection), no recovery prompt

### Scenario 8: Edge - Blocked User During Resume

**Purpose**: Verify blocked users don't break resume

1. Have one recipient block the bot
2. Start batch, interrupt before reaching blocked user
3. Resume batch
4. **Expected**:
   - Blocked user marked as `failed`
   - Other recipients receive messages
   - Error logged but not shown to organizer (except in report)

### Scenario 9: Truncation + Special Characters

**Purpose**: Verify truncation handles UTF-8 correctly

1. Create guest with projects containing emoji, Cyrillic, special chars
2. Send reminder
3. **Expected**:
   - Message is valid UTF-8
   - No broken characters at truncation point
   - Length check accounts for multi-byte chars

### Scenario 10: Full E2E - All Roles

**Purpose**: Complete flow validation

1. Set up test data: students, experts, guests, business
2. Run `/remind` → "За день" → Confirm
3. **Expected**:
   - All roles receive appropriate messages
   - Long programs truncated correctly
   - Report shows accurate counts per role

## Validation Checklist

- [ ] Scenario 1: Short program - no truncation
- [ ] Scenario 2: Long program - correct truncation
- [ ] Scenario 3: Interrupted batch detected
- [ ] Scenario 4: Resume sends only pending
- [ ] Scenario 5: Fresh start cancels old
- [ ] Scenario 6: Only newest batch shown
- [ ] Scenario 7: Completed batch not recovered
- [ ] Scenario 8: Blocked user handled gracefully
- [ ] Scenario 9: UTF-8 truncation safe
- [ ] Scenario 10: Full E2E passes
