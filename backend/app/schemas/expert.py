import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field


class ExpertUploadRow(BaseModel):
    id: str
    name: str
    telegram: str = ""
    expertise_tags: list[str] = []
    position: str = ""
    dd_status: str = ""
    inviter: str | None = None


class RowError(BaseModel):
    row: int
    field: str
    message: str


class ExpertUploadResult(BaseModel):
    total_parsed: int
    imported: int
    with_tags: int
    without_tags: int
    errors: list[RowError] = []


class ReplaceConfirmation(BaseModel):
    existing_count: int
    message: str


class ExpertResponse(BaseModel):
    id: uuid.UUID
    seed_id: str
    name: str
    telegram_username: str | None = None
    position: str | None = None
    tags: list[str] = []
    bot_started: bool = False
    assignment_status: str | None = None

    model_config = {"from_attributes": True}


class AssignmentResponse(BaseModel):
    id: uuid.UUID
    expert_id: uuid.UUID
    room_id: uuid.UUID
    room_name: str = ""
    match_score: float
    is_manual: bool
    status: str

    model_config = {"from_attributes": True}


class ExpertDetailResponse(ExpertResponse):
    inviter: str | None = None
    dd_status_seed: str | None = None
    assignment: AssignmentResponse | None = None


class MatchingRequest(BaseModel):
    use_adjacent_tags: bool = True


class RoomMatchExpert(BaseModel):
    expert_id: uuid.UUID
    name: str
    match_score: float
    matching_tags: list[str] = []
    is_manual: bool = False


class RoomMatchSummary(BaseModel):
    room_id: uuid.UUID
    room_name: str
    expert_count: int
    experts: list[RoomMatchExpert] = []


class MatchingResult(BaseModel):
    clustering_run_id: uuid.UUID
    total_experts: int
    matched_experts: int
    unmatched_experts: int
    rooms: list[RoomMatchSummary] = []


class MoveExpertRequest(BaseModel):
    target_room_id: uuid.UUID


class ApproveResult(BaseModel):
    approved_count: int
    message: str


class InvitePreview(BaseModel):
    total_experts: int
    with_telegram: int
    without_telegram: int
    sample_message: str
    bot_link: str


class InviteConfirmResult(BaseModel):
    invite_ready_count: int
    bot_link: str
    message: str


class RoomCoverageSummary(BaseModel):
    room_id: uuid.UUID
    room_name: str
    needed: int = 2
    confirmed: int = 0
    declined: int = 0
    no_response: int = 0
    not_in_bot: int = 0
    coverage_level: str = "uncovered"


class CoverageDashboard(BaseModel):
    event_date: date | None = None
    rooms: list[RoomCoverageSummary] = []
    totals: dict = Field(default_factory=lambda: {
        "total_needed": 0,
        "confirmed": 0,
        "declined": 0,
        "no_response": 0,
        "coverage_percent": 0.0,
    })


class RoomExpertDetail(BaseModel):
    expert_id: uuid.UUID
    name: str
    status: str
    match_score: float
    is_manual: bool
    bot_started: bool


class AdjacentExpert(BaseModel):
    expert_id: uuid.UUID
    name: str
    adjacent_tags: list[str] = []


class RoomCoverageDetail(BaseModel):
    room_id: uuid.UUID
    room_name: str
    experts: list[RoomExpertDetail] = []
    suggested_adjacent: list[AdjacentExpert] = []


class ExpertCreateRequest(BaseModel):
    name: str
    telegram_username: str | None = None
    position: str | None = None
    tags: list[str] = []


class ExpertUpdateRequest(BaseModel):
    name: str | None = None
    telegram_username: str | None = None
    position: str | None = None
    tags: list[str] | None = None


class EscalationResponse(BaseModel):
    id: uuid.UUID
    type: str
    expert_name: str
    room_name: str
    message: str
    created_at: datetime
    resolved: bool
