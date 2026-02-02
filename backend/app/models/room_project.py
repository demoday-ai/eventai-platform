import uuid

from sqlalchemy import Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class RoomProject(Base):
    __tablename__ = "room_projects"
    __table_args__ = (
        UniqueConstraint("room_id", "project_id", name="uq_room_projects_room_project"),
    )

    room_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    is_manual: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    room = relationship("Room", back_populates="project_assignments")
    project = relationship("Project", back_populates="room_assignments")
