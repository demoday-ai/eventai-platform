"""Pydantic schemas for schedule and notification endpoints."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel

# === Schedule Slot Schemas ===


class ScheduleSlotResponse(BaseModel):
    id: UUID
    room_id: UUID
    room_name: str
    slot_type: str = "project"
    title: str | None = None
    project_id: UUID | None = None
    project_title: str | None = None
    project_author: str | None = None
    project_description: str | None = None
    start_time: datetime
    end_time: datetime
    display_order: int
    status: str

    class Config:
        from_attributes = True


class RoomTimeOverride(BaseModel):
    room_id: UUID
    start_time: str  # "HH:MM"
    end_time: str  # "HH:MM"


class BreakTime(BaseModel):
    start_time: str  # "HH:MM"
    end_time: str  # "HH:MM"


class ScheduleGenerateRequest(BaseModel):
    clustering_run_id: UUID | None = None
    day1_start: datetime | None = None
    day1_end: datetime | None = None
    day2_start: datetime | None = None
    day2_end: datetime | None = None
    slot_duration_minutes: int = 15
    room_overrides: list[RoomTimeOverride] = []
    breaks: list[BreakTime] = []
    force: bool = False


class RoomSummary(BaseModel):
    room_id: UUID
    room_name: str
    slot_count: int
    first_slot: datetime | None = None
    last_slot: datetime | None = None


class ScheduleGenerateResult(BaseModel):
    total_slots: int
    unplaced_count: int = 0
    rooms: list[RoomSummary]


class SlotUpdateRequest(BaseModel):
    start_time: datetime | None = None
    end_time: datetime | None = None
    room_id: UUID | None = None
    status: str | None = None  # "scheduled" or "cancelled"


class SlotUpdateResult(BaseModel):
    slot: ScheduleSlotResponse
    change_log_id: UUID
    notifications_queued: int


class RoomSchedule(BaseModel):
    room_id: UUID
    room_name: str
    slots: list[ScheduleSlotResponse]


class DaySchedule(BaseModel):
    date: date
    rooms: list[RoomSchedule]


class ScheduleResponse(BaseModel):
    event_name: str
    days: list[DaySchedule]


# === Schedule Builder Schemas ===


class SlotCreateRequest(BaseModel):
    """Create a slot manually (drag from sidebar or special block)."""
    room_id: UUID
    start_time: datetime
    end_time: datetime
    slot_type: str = "project"
    project_id: UUID | None = None
    title: str | None = None
    description: str | None = None


class SlotCreateResponse(BaseModel):
    slot: ScheduleSlotResponse


class UnplacedProject(BaseModel):
    id: UUID
    title: str
    author: str
    tags: list[str] = []


class UnplacedResponse(BaseModel):
    total: int
    items: list[UnplacedProject]


class BulkMoveRequest(BaseModel):
    room_id: UUID
    after_time: datetime
    shift_minutes: int


class BulkMoveResponse(BaseModel):
    moved_count: int


class ScheduleConfigBreak(BaseModel):
    start_time: str  # "HH:MM"
    end_time: str  # "HH:MM"
    label: str = "Перерыв"


class ScheduleConfigCeremony(BaseModel):
    start_time: str  # "HH:MM"
    end_time: str  # "HH:MM"
    label: str


class ScheduleConfigParsedDay(BaseModel):
    """Временная рамка одного дня. Залы НЕ описываются — они уже есть из кластеризации."""
    date_hint: str  # "первый день", "22 января", ...
    start_time: str = "10:00"  # "HH:MM"
    end_time: str = "19:30"  # "HH:MM"
    slot_duration_minutes: int = 15
    format: str = "presentation_15min"
    track_filter: str | None = None  # "all_except_research" | "research_only" | "business" | "roasting" | null
    breaks: list[ScheduleConfigBreak] = []
    ceremonies: list[ScheduleConfigCeremony] = []


class ScheduleConfigFromTextRequest(BaseModel):
    text: str


class ScheduleConfigFromTextResponse(BaseModel):
    parsed_config: list[ScheduleConfigParsedDay]
    rooms_count: int  # Сколько залов уже есть из кластеризации
    message: str


# === Reminder Schemas ===


class RecipientCounts(BaseModel):
    students: int = 0
    experts: int = 0
    guests: int = 0
    business: int = 0
    total: int = 0


class SampleMessages(BaseModel):
    student: str | None = None
    expert: str | None = None
    guest: str | None = None
    business: str | None = None


class UnreachableParticipant(BaseModel):
    user_id: UUID | None = None
    name: str
    role: str
    reason: str


class ReminderPreview(BaseModel):
    day: date
    scheduled_send_time: datetime
    can_cancel: bool
    recipients: RecipientCounts
    sample_messages: SampleMessages
    unreachable: list[UnreachableParticipant]


class ReminderSendResult(BaseModel):
    day: date
    sent: int
    failed: int
    skipped: int


class ReminderCancelRequest(BaseModel):
    day: date


class ReminderCancelResult(BaseModel):
    cancelled_count: int
    day: date


class ReminderSendRequest(BaseModel):
    day: date


# === Notification Dashboard Schemas ===


class StatusSummary(BaseModel):
    total: int = 0
    sent: int = 0
    failed: int = 0
    pending: int = 0


class RoleStats(BaseModel):
    role: str
    sent: int = 0
    failed: int = 0
    pending: int = 0


class TypeStats(BaseModel):
    type: str
    sent: int = 0
    failed: int = 0
    pending: int = 0


class NotificationDashboard(BaseModel):
    summary: StatusSummary
    by_role: list[RoleStats]
    by_type: list[TypeStats]
    unreachable: list[UnreachableParticipant]


class NotificationItem(BaseModel):
    id: UUID
    user_name: str | None = None
    type: str
    status: str
    scheduled_at: datetime | None = None
    sent_at: datetime | None = None
    error_message: str | None = None
    retry_count: int = 0

    class Config:
        from_attributes = True


class NotificationListResponse(BaseModel):
    total: int
    items: list[NotificationItem]


# === Schedule Change Log Schemas ===


class ScheduleChangeItem(BaseModel):
    id: UUID
    slot_id: UUID
    project_title: str | None = None
    change_type: str
    old_start_time: datetime | None = None
    new_start_time: datetime | None = None
    old_room_name: str | None = None
    new_room_name: str | None = None
    changed_by: str | None = None
    created_at: datetime
    notifications_sent: bool

    class Config:
        from_attributes = True


class ScheduleChangeListResponse(BaseModel):
    total: int
    items: list[ScheduleChangeItem]


# === Schedule Approval ===


class ScheduleApproveResult(BaseModel):
    total_slots: int
    rooms: int
    days: int
