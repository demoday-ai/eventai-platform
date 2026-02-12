import uuid

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Room(Base):
    __tablename__ = "rooms"

    clustering_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clustering_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    theme_rationale: Mapped[str] = mapped_column(Text, nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    moderator: Mapped[str | None] = mapped_column(String(200), nullable=True)
    platform: Mapped[str | None] = mapped_column(String(50), nullable=True)
    slot_duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=15)
    day_number: Mapped[int | None] = mapped_column(Integer, nullable=True)

    clustering_run = relationship("ClusteringRun", back_populates="rooms")
    project_assignments = relationship("RoomProject", back_populates="room", cascade="all, delete-orphan")
