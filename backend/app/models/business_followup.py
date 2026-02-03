"""Business Follow-up model for EPIC-015: Business Follow-up.

Tracks business partner interactions with projects after Demo Day.
"""

import enum
import uuid
from datetime import datetime
from sqlalchemy import Boolean, Enum, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class PipelineStatus(str, enum.Enum):
    """Status of a project in partner's pipeline."""
    interested = "interested"
    contacted = "contacted"
    negotiating = "negotiating"
    closed_won = "closed_won"
    closed_lost = "closed_lost"


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
    status: Mapped[PipelineStatus] = mapped_column(
        Enum(PipelineStatus),
        default=PipelineStatus.interested,
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
            PipelineStatus.interested: "👀",
            PipelineStatus.contacted: "📧",
            PipelineStatus.negotiating: "🤝",
            PipelineStatus.closed_won: "✅",
            PipelineStatus.closed_lost: "❌",
        }.get(self.status, "❓")
