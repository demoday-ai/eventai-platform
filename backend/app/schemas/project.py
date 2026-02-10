import uuid
from typing import Literal

from pydantic import BaseModel, Field, field_validator

TrackType = Literal["Индустриальный", "Стартап", "Образовательный", "Научный"]


class ProjectUploadRow(BaseModel):
    title: str
    description: str
    tags: str  # comma-separated
    author: str
    telegram_contact: str
    track: TrackType | None = None

    @field_validator("track", mode="before")
    @classmethod
    def validate_track(cls, v):
        if v is None or v == "":
            return None
        # Normalize to lowercase for matching
        v_lower = str(v).strip().lower()
        # Map all variants to canonical Russian names with capital letter
        track_map = {
            "industrial": "Индустриальный",
            "индустриальный": "Индустриальный",
            "индустриал": "Индустриальный",
            "startup": "Стартап",
            "стартап": "Стартап",
            "educational": "Образовательный",
            "образовательный": "Образовательный",
            "образование": "Образовательный",
            "edtech": "Образовательный",
            "research": "Научный",
            "научный": "Научный",
            "наука": "Научный",
        }
        normalized = track_map.get(v_lower)
        if normalized is None:
            raise ValueError(f"Track must be one of: Индустриальный, Стартап, Образовательный, Научный. Got: {v}")
        return normalized


class RowError(BaseModel):
    row: int
    field: str
    message: str


class UploadResult(BaseModel):
    loaded: int
    errors: int
    duplicates: int
    error_details: list[RowError] = []
    duplicate_titles: list[str] = []
    duplicate_warning: str | None = None


class ReplaceConfirmation(BaseModel):
    message: str
    existing_count: int
    new_count: int


class ProjectResponse(BaseModel):
    id: uuid.UUID
    title: str
    description: str
    tags: list[str]
    author: str
    telegram_contact: str
    track: str | None = None
    source: str
    room: "RoomSummary | None" = None

    model_config = {"from_attributes": True}


class RoomSummary(BaseModel):
    id: uuid.UUID
    name: str

    model_config = {"from_attributes": True}


class ClusteringRequest(BaseModel):
    num_rooms: int = Field(default=6, ge=2, le=20)
    feedback: str | None = None
    room_themes: list[str] | None = None


class RoomSchema(BaseModel):
    id: uuid.UUID
    name: str
    theme_rationale: str
    project_count: int
    projects: list[ProjectResponse] = []

    model_config = {"from_attributes": True}


class ClusteringResult(BaseModel):
    id: uuid.UUID
    status: str
    num_rooms: int
    feedback: str | None = None
    rooms: list[RoomSchema] = []
    created_at: str
    approved_at: str | None = None

    model_config = {"from_attributes": True}


class MoveProjectRequest(BaseModel):
    project_id: uuid.UUID
    target_room_id: uuid.UUID
