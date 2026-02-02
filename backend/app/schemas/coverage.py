"""Pydantic schemas for EPIC-006: Organizer Coverage Dashboard."""

import uuid

from pydantic import BaseModel


class RoomCoverage(BaseModel):
    room_id: uuid.UUID
    room_name: str
    project_count: int = 0
    top_tags: list[str] = []
    confirmed: int = 0
    pending: int = 0
    declined: int = 0
    total_assigned: int = 0
    coverage_level: str = "uncovered"  # covered | partial | uncovered


class CoverageSummary(BaseModel):
    rooms: list[RoomCoverage] = []
    totals: dict = {}


class RoomExpert(BaseModel):
    expert_id: uuid.UUID
    name: str
    status: str
    match_score: float = 0.0
    tags: list[str] = []
    bot_started: bool = False


class ExpertCandidate(BaseModel):
    expert_id: uuid.UUID
    name: str
    matching_tags: list[str] = []
    current_rooms: list[str] = []


class CoverageGap(BaseModel):
    room_id: uuid.UUID
    room_name: str
    uncovered_tag: str
    project_count_with_tag: int = 0
    candidates: list[ExpertCandidate] = []


class RoomCoverageDetail(BaseModel):
    room_id: uuid.UUID
    room_name: str
    project_count: int = 0
    project_tags: list[str] = []
    experts: list[RoomExpert] = []
    uncovered_tags: list[str] = []
    candidates: list[ExpertCandidate] = []


class CoverageGapsList(BaseModel):
    total_gaps: int = 0
    gaps: list[CoverageGap] = []
