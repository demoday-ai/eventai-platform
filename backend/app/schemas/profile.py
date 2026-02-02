"""Pydantic schemas for business profile endpoints."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.business_profile import BusinessObjective


class BusinessProfileCreate(BaseModel):
    """Schema for creating/updating a business profile."""

    user_id: UUID
    event_id: UUID
    objective: BusinessObjective
    industries: list[str] | None = Field(default=None, max_length=10)
    tech_stack: list[str] | None = Field(default=None, max_length=15)
    project_stages: list[str] | None = None
    collaboration_format: str | None = Field(default=None, max_length=500)
    free_text_raw: str | None = Field(default=None, max_length=2000)


class BusinessProfileResponse(BaseModel):
    """Schema for business profile response."""

    id: UUID
    user_id: UUID
    event_id: UUID
    objective: BusinessObjective
    industries: list[str] | None = None
    tech_stack: list[str] | None = None
    project_stages: list[str] | None = None
    collaboration_format: str | None = None
    free_text_raw: str | None = None
    free_text_parsed: dict | None = None
    created_at: datetime
    updated_at: datetime
    recommendations_count: int = 0

    model_config = {"from_attributes": True}


class ExtractedProfile(BaseModel):
    """Schema for LLM-extracted profile from free text."""

    objective: BusinessObjective | None = None
    industries: list[str] = Field(default_factory=list)
    tech_stack: list[str] = Field(default_factory=list)
    project_stages: list[str] = Field(default_factory=list)
    collaboration_format: str | None = None
    parsed_interests: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class ExtractRequest(BaseModel):
    """Schema for profile extraction request."""

    text: str = Field(..., max_length=2000)
    objective: BusinessObjective | None = None


class ProjectRecommendationResponse(BaseModel):
    """Schema for a single project recommendation."""

    id: UUID
    project_id: UUID
    project_title: str
    project_description: str
    project_author: str
    project_tags: list[str] = Field(default_factory=list)
    hall: str | None = None
    time_slot: str | None = None
    relevance_score: int = Field(..., ge=0, le=100)
    relevance_explanation: str | None = None
    rank: int
    is_bookmarked: bool = False
    is_viewed: bool = False

    model_config = {"from_attributes": True}


class RecommendationsPage(BaseModel):
    """Schema for paginated recommendations."""

    items: list[ProjectRecommendationResponse]
    total: int
    page: int
    page_size: int
    has_next: bool


class RecommendationUpdate(BaseModel):
    """Schema for updating recommendation status."""

    is_viewed: bool | None = None
    is_bookmarked: bool | None = None
