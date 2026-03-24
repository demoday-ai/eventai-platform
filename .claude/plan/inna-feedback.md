# Implementation Plan: Доработки DemoDay AI по фидбеку Инны

## Task Type
- [x] Fullstack (-> Parallel backend + frontend)

## Source Documents
- Brief: `docs/02-specification/01a-brief-inna-feedback.md`
- USM: `docs/02-specification/02a-user-story-map-inna-feedback.md`
- NFR: `docs/02-specification/04a-nfr-inna-feedback.md`

---

## Phase 0: Infrastructure prep (before features)

### Step 0.1: Decompose start.py bot handler
- **Why:** start.py = 1489 строк, 6 состояний. P3 и P4 добавят 3+ новых хендлера. Без декомпозиции файл станет неуправляемым.
- **Files:** `backend/app/bot/handlers/start.py` -> split into `expert_handler.py`, `chat_handler.py`, `feedback_handler.py`
- **Deliverable:** Existing functionality preserved, tests pass, file < 800 lines each

### Step 0.2: Reusable frontend components
- **Why:** 13 фич будут дублировать UI-паттерны
- **Files:** Create `frontend/src/components/shared/`
- **Components:** `InlineEditableText`, `NotificationBadge`, `TimelineMini`, `AddScheduleBlockDialog`
- **Tests:** Unit tests on keyboard interactions, cancel/save, disabled state

---

## P1: Quick Fixes

### 1. Fix coffee-break and section buttons in Schedule
| Aspect | Details |
|--------|---------|
| Backend | `schedule_service.py`: validate `slot_type=break\|section` in `create_slot()`. `schemas/schedule.py`: add `title` to `SlotCreateRequest` |
| Frontend | `ScheduleToolbar.tsx`: wire `onAddBreak`/`onAddSection` to open `AddScheduleBlockDialog`. Dialog: room selector, time range, title (for section). After submit -> `createSlot()` -> `invalidateQueries(["schedule"])` |
| Migration | None |
| Tests | RTL: click buttons -> dialog opens. Backend: create break/section slot via API |

### 2. "Contact organizers" button in bot
| Aspect | Details |
|--------|---------|
| Backend | `keyboards.py`: add `contact_organizers_button()`. `start.py` (or new `chat_handler.py`): callback handler forwards message to `team_chat_id` via `messaging_service`. Quick fix without DB - just forward text to organizer group |
| Frontend | None |
| Migration | None |
| Tests | Bot handler test: callback delivers message to organizer list |

### 3. Configurable min experts per room
| Aspect | Details |
|--------|---------|
| Backend | `models/event.py`: add `min_experts_per_room` (Integer, default=2). `matching_service.py`: use in coverage calculation. `api/admin/events.py`: expose in PATCH |
| Frontend | `Settings.tsx` or `ExpertMatching.tsx` step 0: Input field with validation. Show deficit warning |
| Migration | `033_add_min_experts_per_room.py`: add column to events |
| Tests | Migration test, API PATCH test, matching service test on deficit detection |

### 4. Add/edit students and project names
| Aspect | Details |
|--------|---------|
| Backend | `api/admin/projects.py`: add `POST /admin/projects` (create project), extend `PATCH /admin/projects/:id` for title/author edit. `api/admin/guests.py`: add student CRUD if needed |
| Frontend | `ProjectsList.tsx`: inline edit title (double-click -> input -> Enter/Esc). `ProjectDetail.tsx`: edit author, add student modal |
| Migration | None (use existing models) |
| Tests | API CRUD tests, RTL: Enter saves, Esc cancels, simultaneous edits prevented |

### 5. Reminders to students AND experts 30 min before slots
| Aspect | Details |
|--------|---------|
| Backend | `notification_service.py`: ensure `preview_reminders()` and `send_eve_reminders()` include both `ParticipationRequest` users AND `ExpertRoomAssignment` experts. Change window from 60min to 30min |
| Frontend | `RemindersTab.tsx`: show separate preview cards for students and experts |
| Migration | None |
| Tests | Unit test: both segments in recipient list. Dedup test. Window 25-35 min test |

---

## P2: Advanced Clustering

### 6. Flexible clustering parameters
| Aspect | Details |
|--------|---------|
| Backend | `models/clustering_run.py`: add `constraints` (JSONB) for max_projects_per_room, breaks, time_limits. `clustering_service.py`: pass constraints to LLM prompt. `prompts/admin/clustering.py`: extend prompt template |
| Frontend | `Clustering.tsx` step 0: `AdvancedClusteringParams` section with fields: max projects (input), break duration (input), day time limits (time pickers) |
| Migration | `033_clustering_constraints.py`: add JSONB column |
| Tests | Schema validation, service test on max-per-room enforcement, prompt test |

### 7. Business/roast projects in one room
| Aspect | Details |
|--------|---------|
| Backend | `models/project.py`: add `defense_format` enum (normal/business/roast). `clustering_service.py`: pre-group by format before LLM clustering |
| Frontend | `ProjectDetail.tsx`: Select dropdown for format. `ProjectsList.tsx`: badge |
| Migration | `034_project_defense_format.py`: add enum column |
| Tests | Clustering test: same-format projects co-located. Admin update test |

### 8. Similar topics not in parallel
| Aspect | Details |
|--------|---------|
| Backend | `schedule_service.py`: in `generate_schedule()`, compute tag overlap between rooms. If overlap > 50%, offset in time. Add `warnings` to `ScheduleGenerateResult` |
| Frontend | `Schedule.tsx`: `ParallelTopicWarningsCard` after generation. Checkbox in config |
| Migration | None |
| Tests | Service test: conflicting pairs separated. Warning serialization test |

### 9. Multiple clustering variants (2-3)
| Aspect | Details |
|--------|---------|
| Backend | `models/clustering_run.py`: add `variant_group_id` (UUID), `variant_label` (str). `clustering_service.py`: `run_clustering(variant_count=3)` -> create N runs with same group_id. New endpoint: `GET /clustering/variants` |
| Frontend | `Clustering.tsx` step 1: Tabs for each variant. Compare: room count, balance, forced groups. Approve specific variant -> supersede others |
| Migration | `035_clustering_variants.py`: add variant columns |
| Tests | Async job on batch generation. Approve supersedes siblings. Frontend tab switching |

### 10. Auto-generate schedule from approved clustering
| Aspect | Details |
|--------|---------|
| Backend | Already supported: `generateSchedule(clustering_run_id)`. Add schedule preview summary to clustering approve response |
| Frontend | `Clustering.tsx` step 3: after approve, CTA "Сгенерировать расписание". Navigate to `/schedule` with `{ fromClustering: true }` state. Auto-trigger generation |
| Migration | None |
| Tests | Approve -> navigate -> auto-generate. No infinite loop on remount |

---

## P3: Expert Pipeline

### 11. Flexible matching (consider position)
| Aspect | Details |
|--------|---------|
| Backend | `matching_service.py`: add position-based scoring. Map position keywords to tags (e.g. "ML Engineer" -> ML). Weight: tags 70% + position 30%. Field `position` already exists on Expert model |
| Frontend | `ExpertMatching.tsx`: show position under name, show match breakdown (tags + position) |
| Migration | None |
| Tests | Scoring mix unit tests. Fallback without position |

### 12. Time slots in expert matching UI
| Aspect | Details |
|--------|---------|
| Backend | `api/experts/matching.py`: include room schedule summary (time range, slot count) in `getCurrentMatching()` response |
| Frontend | `ExpertMatching.tsx` step 1: `TimelineMini` strip next to room cards showing slot ranges |
| Migration | None |
| Tests | API serialization test. RTL: slots visible when schedule exists, empty state without |

### 13. Expert availability through bot
| Aspect | Details |
|--------|---------|
| Backend | New handler `expert_handler.py`: ConversationHandler states CHOOSE_DAYS -> CHOOSE_SLOTS -> CONFIRM. `models/expert_room_assignment.py`: add `availability_payload` (JSONB), `availability_submitted_at`. `invite_service.py`: send availability prompt after invitation |
| Frontend | Coverage/ExpertMatching: indicator "availability collected / pending" |
| Migration | `036_expert_availability.py`: add columns |
| Tests | Bot conversation test. Migration test. Service test on availability write |

### 14. Confirm/change room buttons for expert
| Aspect | Details |
|--------|---------|
| Backend | `expert_handler.py`: after matching, send room proposal with InlineKeyboard ["Подтверждаю" / "Хочу поменять"]. Update `ExpertRoomAssignment.status` accordingly. Use existing statuses: invited -> confirmed or invited -> reassign_requested |
| Frontend | ExpertMatching: show last bot action per expert |
| Migration | None (use status field + availability from #13) |
| Tests | Callback tests on confirm/change flow. Status transition tests |

### 15. Notification on room change request
| Aspect | Details |
|--------|---------|
| Backend | `expert_handler.py`: on "Хочу поменять" -> create audit log entry + send Telegram notification to `team_chat_id`. `dashboard_service.py`: include reassign_requested count in alerts |
| Frontend | Dashboard: alert "N экспертов запросили смену комнаты". ExpertMatching: badge |
| Migration | None |
| Tests | Fan-out notification test. Dashboard alert test |

### 16. Skip slot selection for unrestricted experts
| Aspect | Details |
|--------|---------|
| Backend | `expert_handler.py`: "Доступен весь день" option in CHOOSE_DAYS. If selected -> skip CHOOSE_SLOTS -> go straight to room proposal. Set `availability_payload = {"all_day": true}` |
| Frontend | Read-only label "без ограничений" in matching UI |
| Migration | None (uses #13 fields) |
| Tests | Bot branching test on skip path |

---

## P4: Communications & Analytics

### 17. Moderators in schedule
| Aspect | Details |
|--------|---------|
| Backend | `models/room.py`: field `moderator` already exists. `api/admin/rooms.py`: expose in PATCH. `api/schedule.py`: add `?moderator=` filter to XLSX export |
| Frontend | `RoomDetail.tsx`: edit moderator field. `Schedule.tsx`: show moderator name in room header. Export: "По модератору" filter button |
| Migration | None |
| Tests | API export filter test. RTL: moderator edit and display |

### 18. Full chat support (bot <-> admin)
| Aspect | Details |
|--------|---------|
| Backend | New models: `SupportThread` (user_id, event_id, status, last_message_at), `SupportMessage` (thread_id, sender_type, text, created_at). New handler `chat_handler.py`: any text in CONTACT_ORGANIZERS state -> create/append to thread. New API: `GET /admin/support/threads`, `GET /admin/support/threads/:id/messages`, `POST /admin/support/threads/:id/reply`, `POST /admin/support/threads/:id/resolve` |
| Frontend | New route `/support-chat`. Page: `SupportChat.tsx` with two-panel layout (ConversationList + ChatPanel). Polling every 3s via `refetchInterval`. `NotificationBadge` in Sidebar. Counter in header |
| Migration | `037_support_chat.py`: create support_threads + support_messages tables |
| Tests | API thread lifecycle. Bot inbound routing. Frontend polling + scroll preservation |

### 19. Expert feedback through bot
| Aspect | Details |
|--------|---------|
| Backend | New model: `ExpertEvaluation` (expert_id, project_id, room_id, event_id, ratings JSONB, comment, submitted_at). New handler in `expert_handler.py`: after each slot, prompt evaluation (7 criteria, scale 1-3). `dashboard_service.py`: aggregate by room/project/criterion. New API: `GET /admin/feedback/dashboard`, `GET /admin/feedback/export` |
| Frontend | `Dashboard.tsx`: `ExpertFeedbackWidget` (progress bar, avg scores by room, top/bottom 5). New Messaging tab or separate page for detailed view |
| Migration | `038_expert_evaluation.py`: create table |
| Tests | Bot submission test. Aggregation tests. Dashboard widget rendering |

---

## Implementation Order

```
Phase 0: Bot decomposition + shared components (2 days)
  |
  v
P1: Quick fixes - items 1-5 (3 days)
  |
  v
P2.6 + P2.9: Clustering params + variants (3 days)
  |
  v
P2.7 + P2.8 + P2.10: Format tags + parallel check + schedule gen (2 days)
  |
  v
P3.11 + P3.12: Position matching + time slots UI (2 days)
  |
  v
P3.13-16: Expert bot pipeline as one batch (4 days)
  |
  v
P4.17: Moderators (1 day)
  |
  v
P4.18: Chat support (3 days)
  |
  v
P4.19: Expert feedback (3 days)
```

## Risks and Mitigation

| Risk | Mitigation |
|------|------------|
| start.py decomposition breaks existing bot flow | Phase 0 first, full test coverage before features |
| Multiple clustering variants = 3x LLM cost | Default to 2 variants, cap at 3, progress bar mandatory |
| Chat polling (3s) adds API load | Lightweight endpoint, pagination, connection reuse |
| Expert bot pipeline complex (4+ states) | Separate ConversationHandler, not extension of main one |
| One developer, large scope | Each priority group delivers value independently |

## Key Files Summary

| File | Operations | Features |
|------|-----------|----------|
| `backend/app/bot/handlers/start.py` | Split | Phase 0 |
| `backend/app/bot/handlers/expert_handler.py` | Create | P3.13-16, P4.19 |
| `backend/app/bot/handlers/chat_handler.py` | Create | P1.2, P4.18 |
| `backend/app/services/admin/clustering_service.py` | Modify | P2.6,7,8,9 |
| `backend/app/services/admin/schedule_service.py` | Modify | P2.8,10 |
| `backend/app/services/admin/matching_service.py` | Modify | P1.3, P3.11 |
| `backend/app/services/admin/notification_service.py` | Modify | P1.5, P3.15 |
| `backend/app/models/clustering_run.py` | Modify | P2.6,9 |
| `backend/app/models/project.py` | Modify | P2.7 |
| `backend/app/models/expert_room_assignment.py` | Modify | P3.13 |
| `frontend/src/pages/Clustering.tsx` | Modify | P2.6,8,9,10 |
| `frontend/src/pages/Schedule.tsx` | Modify | P1.1, P2.10 |
| `frontend/src/pages/ExpertMatching.tsx` | Modify | P1.3, P3.11,12 |
| `frontend/src/pages/Dashboard.tsx` | Modify | P4.19 |
| `frontend/src/pages/SupportChat.tsx` | Create | P4.18 |
| `frontend/src/lib/api-client.ts` | Modify | All features |
| Migrations (033-038) | Create | P1.3, P2.6,7,9, P3.13, P4.18,19 |

## SESSION_ID (for /ccg:execute)
- CODEX_SESSION (backend): 019d1fe9-5c04-7ba0-86f2-39ef1539bd16
- CODEX_SESSION (frontend): 019d1fec-f7ec-73a0-97c5-b479f55f34c9
