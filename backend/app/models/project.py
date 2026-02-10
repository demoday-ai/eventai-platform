import uuid

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Project(Base):
    __tablename__ = "projects"
    __table_args__ = (
        UniqueConstraint("event_id", "title", name="uq_projects_event_title"),
    )

    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    author: Mapped[str] = mapped_column(String(300), nullable=False)
    telegram_contact: Mapped[str] = mapped_column(String(100), nullable=False)
    track: Mapped[str | None] = mapped_column(String(50), nullable=True)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="upload")

    # EPIC-008: Additional fields for expert briefing
    github_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    tech_stack: Mapped[str | None] = mapped_column(String(500), nullable=True)
    presentation_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    demo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    tags = relationship("ProjectTag", back_populates="project", cascade="all, delete-orphan")
    room_assignments = relationship(
        "RoomProject", back_populates="project", cascade="all, delete-orphan"
    )
