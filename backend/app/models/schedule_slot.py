"""Schedule slot model - a time block for a project presentation."""

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class SlotStatus(str, Enum):
    SCHEDULED = "scheduled"
    MOVED = "moved"
    CANCELLED = "cancelled"


class ScheduleSlot(Base):
    __tablename__ = "schedule_slots"
    __table_args__ = (
        UniqueConstraint("project_id", "clustering_run_id", name="uq_slot_project_run"),
        Index("ix_schedule_slots_event_id", "event_id"),
        Index("ix_schedule_slots_room_id", "room_id"),
        Index("ix_schedule_slots_project_id", "project_id"),
        Index("ix_schedule_slots_start_time", "start_time"),
        Index("ix_schedule_slots_status", "status"),
    )

    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=False
    )
    room_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    clustering_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clustering_runs.id", ondelete="CASCADE"),
        nullable=False,
    )

    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=SlotStatus.SCHEDULED.value)
    status_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, onupdate=datetime.utcnow
    )

    # Relationships
    event = relationship("Event")
    room = relationship("Room")
    project = relationship("Project")
    clustering_run = relationship("ClusteringRun")
    change_logs = relationship("ScheduleChangeLog", back_populates="schedule_slot", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="schedule_slot")
