from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base


class ScheduleSlot(Base):
    __tablename__ = "schedule_slots"
    __table_args__ = (
        UniqueConstraint("room_id", "start_time"),
    )

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )
    event_id: Mapped[UUID] = mapped_column(
        ForeignKey("events.id"),
        index=True,
    )
    room_id: Mapped[UUID] = mapped_column(ForeignKey("rooms.id"))
    # 031-bot-replacement: backend schema makes project_id nullable
    # (slots may be placeholders without an assigned project).
    project_id: Mapped[UUID | None] = mapped_column(ForeignKey("projects.id"))
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    # 031-bot-replacement: backend schema uses `display_order` (per-day index),
    # not `day_number`. Bot uses this only as a sort key.
    display_order: Mapped[int] = mapped_column(Integer)
