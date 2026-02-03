"""Feedback Comment model for EPIC-012: Student Feedback.

Stores expert feedback on student projects with AI processing.
"""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class FeedbackCategory(str, enum.Enum):
    """Category of feedback."""
    TECHNICAL = "technical"
    PRODUCT = "product"
    PRESENTATION = "presentation"
    GENERAL = "general"


class ModerationStatus(str, enum.Enum):
    """Status of feedback moderation."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EDITED = "edited"


class FeedbackComment(Base):
    """Expert feedback on a student project."""

    __tablename__ = "feedback_comments"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    expert_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("experts.id", ondelete="CASCADE"),
        nullable=False,
    )
    original_text: Mapped[str] = mapped_column(Text, nullable=False)
    processed_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str | None] = mapped_column(String(20), nullable=True)
    is_constructive: Mapped[bool] = mapped_column(Boolean, default=True)
    moderation_status: Mapped[str] = mapped_column(
        String(20),
        default=ModerationStatus.PENDING.value,
    )
    moderator_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Relationships
    project = relationship("Project")
    expert = relationship("Expert")
