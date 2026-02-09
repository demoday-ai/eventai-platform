# Research: Schedule Wizard

## R1: Current State

Schedule.tsx (607 lines) — 95% complete wizard with 3 steps. Missing:
1. No confirmation dialog before approve (line 588: direct mutate)
2. No next-step hint after approval (→ /reminders)
3. No pipeline-status + dashboard invalidation after approve

## R2: Tests

Schedule.test.tsx — 13 tests covering generation, viewing, editing, changes. Need 2 more for confirmation + next-step hint.

## R3: API

All endpoints exist. Frontend-only changes needed.
