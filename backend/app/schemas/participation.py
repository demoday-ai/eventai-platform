import uuid
from datetime import datetime

from pydantic import BaseModel


class BroadcastResult(BaseModel):
    sent: int
    skipped: int
    failed: int
    unregistered: int
    unregistered_projects: list[dict]


class RoomSummary(BaseModel):
    room_id: uuid.UUID
    room_name: str
    total: int
    acknowledged: int
    pending: int


class ParticipationSummary(BaseModel):
    total: int
    acknowledged: int
    pending: int
    unregistered: int
    by_room: list[RoomSummary]


class UnacknowledgedStudent(BaseModel):
    request_id: uuid.UUID
    project_title: str
    author_name: str
    telegram_contact: str
    room_name: str
    status: str
    sent_at: datetime | None = None
    reminder_sent: bool = False
    escalated: bool = False


class UnacknowledgedList(BaseModel):
    items: list[UnacknowledgedStudent]
    total: int


class ParticipationRequestDetail(BaseModel):
    id: uuid.UUID
    project_title: str
    author_name: str
    room_name: str
    status: str
    acknowledged_at: datetime | None = None
    reminder_sent_at: datetime | None = None
    escalated_at: datetime | None = None
    created_at: datetime
