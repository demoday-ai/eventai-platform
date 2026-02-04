"""Admin dashboard schemas."""

from datetime import date, datetime

from pydantic import BaseModel

from app.schemas.expert import RowError


class StudentStats(BaseModel):
    """Student statistics."""

    total: int
    confirmed: int
    pending: int
    declined: int


class ExpertStats(BaseModel):
    """Expert statistics."""

    total: int
    confirmed: int
    pending: int
    invited: int


class GuestSubtypeCount(BaseModel):
    """Guest count by subtype."""

    subtype: str
    count: int


class GuestStats(BaseModel):
    """Guest statistics."""

    total: int
    by_subtype: list[GuestSubtypeCount]


class RoomStats(BaseModel):
    """Room statistics."""

    total: int
    with_experts: int
    without_experts: int


class Alert(BaseModel):
    """Dashboard alert."""

    severity: str  # "critical", "warning", "info"
    message: str
    room_id: str | None = None
    room_name: str | None = None


class DashboardResponse(BaseModel):
    """Organizer dashboard response."""

    students: StudentStats
    experts: ExpertStats
    guests: GuestStats
    rooms: RoomStats
    alerts: list[Alert]


class RoomCoverage(BaseModel):
    """Room coverage information."""

    room_id: str
    room_name: str
    total_experts: int
    confirmed_experts: int
    projects_count: int
    coverage_status: str  # "full", "partial", "none"


class CoverageResponse(BaseModel):
    """Coverage response."""

    rooms: list[RoomCoverage]


class RoomInfo(BaseModel):
    """Room information."""

    id: str
    name: str
    description: str


class ExpertInfo(BaseModel):
    """Expert information."""

    id: str
    name: str
    status: str  # "confirmed", "pending", "declined"
    tags: list[str]


class ProjectInfo(BaseModel):
    """Project information."""

    id: str
    title: str
    author: str
    start_time: str
    end_time: str
    status: str  # "confirmed", "pending", "cancelled"


class RoomDetailResponse(BaseModel):
    """Room detail response."""

    room: RoomInfo
    experts: list[ExpertInfo]
    projects: list[ProjectInfo]
    uncovered_topics: list[str]


class ProjectListItem(BaseModel):
    """Project list item."""

    id: str
    title: str
    author: str
    room_id: str
    room_name: str
    start_time: str
    end_time: str
    status: str  # "confirmed", "pending", "cancelled"
    tags: list[str]


class EventUpdateRequest(BaseModel):
    """Request to update event details."""

    name: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    description: str | None = None


class GuestUploadResult(BaseModel):
    """Result of guest bulk upload."""

    total_parsed: int
    imported: int
    duplicates: int
    errors: list[RowError] = []
    duplicate_warning: str | None = None


class BriefingPreview(BaseModel):
    """Briefing preview for organizer."""

    expert_count: int
    with_telegram: int
    without_telegram: int


class BriefingSendResult(BaseModel):
    """Result of sending briefings."""

    sent: int
    failed: int
    skipped: int


class RecipientPreviewItem(BaseModel):
    """Single recipient in messaging preview."""

    user_id: str
    full_name: str
    role: str
    guest_subtype: str | None = None


class MessagingPreviewRequest(BaseModel):
    """Request to preview messaging recipients."""

    template: str
    roles: list[str]
    guest_subtype: str | None = None
    room_id: str | None = None


class MessagingPreviewResponse(BaseModel):
    """Response with messaging preview."""

    recipient_count: int
    sample_message: str
    recipients_preview: list[RecipientPreviewItem]


class MessagingSendRequest(BaseModel):
    """Request to send messages."""

    template: str
    roles: list[str]
    guest_subtype: str | None = None
    room_id: str | None = None


class MessagingSendResult(BaseModel):
    """Result of sending messages."""

    sent: int
    failed: int
    skipped: int


class AuditLogItem(BaseModel):
    """Single audit log entry."""

    id: str
    created_at: datetime
    user_name: str | None = None
    action: str
    entity_type: str | None = None
    entity_id: str | None = None
    details: dict | None = None


class AuditLogResponse(BaseModel):
    """Paginated audit log response."""

    total: int
    items: list[AuditLogItem]


class OrganizerItem(BaseModel):
    """Organizer list item."""

    id: str
    telegram_id: str
    telegram_username: str | None = None
    name: str | None = None
    added_by: str | None = None
    created_at: datetime


class OrganizerCreateRequest(BaseModel):
    """Request to add a new organizer."""

    telegram_id: str
    telegram_username: str | None = None
    name: str | None = None
