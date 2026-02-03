"""Admin dashboard schemas."""

from pydantic import BaseModel


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
