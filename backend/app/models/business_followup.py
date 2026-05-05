"""Business Follow-up model for EPIC-015: Business Follow-up.

Tracks business partner interactions with projects after Demo Day.
"""

import enum
import uuid

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class PipelineStatus(str, enum.Enum):
    """Status of a project in partner's pipeline.

    NOTE: stored as VARCHAR(64) since migration 038_bonus_tables to allow both
    demoday admin values (interested|contacted|negotiating|closed_won|closed_lost)
    and bonus bot values (interested|contacted|meeting_scheduled|rejected|in_progress).
    """

    interested = "interested"
    contacted = "contacted"
    negotiating = "negotiating"
    closed_won = "closed_won"
    closed_lost = "closed_lost"
    # bonus-track-llm values:
    meeting_scheduled = "meeting_scheduled"
    rejected = "rejected"
    in_progress = "in_progress"


class BusinessFollowup(Base):
    """Business partner's follow-up tracking for a project."""

    __tablename__ = "business_followups"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(64),
        default=PipelineStatus.interested.value,
        nullable=False,
    )
    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    loi_generated: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )

    # Relationships
    user = relationship("User")
    event = relationship("Event")
    project = relationship("Project")

    @property
    def status_emoji(self) -> str:
        """Get emoji for current status."""
        return {
            PipelineStatus.interested.value: "👀",
            PipelineStatus.contacted.value: "📧",
            PipelineStatus.negotiating.value: "🤝",
            PipelineStatus.closed_won.value: "✅",
            PipelineStatus.closed_lost.value: "❌",
            PipelineStatus.meeting_scheduled.value: "📅",
            PipelineStatus.rejected.value: "🚫",
            PipelineStatus.in_progress.value: "🔄",
        }.get(self.status, "❓")
