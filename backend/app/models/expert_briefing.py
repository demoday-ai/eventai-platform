"""Expert Briefing model for EPIC-008.

Tracks delivery of project briefings to experts before Demo Day.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class BriefingStatus(str, enum.Enum):
    """Status of briefing delivery."""

    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    SKIPPED = "skipped"  # Expert without room or declined


class ExpertBriefing(Base):
    """Tracks briefing delivery to an expert."""

    __tablename__ = "expert_briefings"

    expert_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("experts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    room_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("rooms.id", ondelete="SET NULL"),
        nullable=True,
    )
    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    status: Mapped[BriefingStatus] = mapped_column(
        Enum(BriefingStatus, name="briefing_status_enum"),
        nullable=False,
        default=BriefingStatus.PENDING,
    )
    project_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    message_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Relationships
    expert = relationship("Expert")
    room = relationship("Room")
    event = relationship("Event")
