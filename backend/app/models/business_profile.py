"""Business profile model for partner profiling."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class BusinessObjective(str, enum.Enum):
    INVESTMENT = "investment"
    HIRING = "hiring"
    TECHNOLOGY = "technology"
    PARTNERSHIP = "partnership"


OBJECTIVE_DISPLAY = {
    BusinessObjective.INVESTMENT: "Инвестиции",
    BusinessObjective.HIRING: "Найм",
    BusinessObjective.TECHNOLOGY: "Технология",
    BusinessObjective.PARTNERSHIP: "Партнёрство",
}


class BusinessProfile(Base):
    __tablename__ = "business_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
    )
    objective: Mapped[BusinessObjective] = mapped_column(
        Enum(BusinessObjective, name="business_objective", create_type=False),
        nullable=False,
    )
    industries: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    tech_stack: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    project_stages: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    collaboration_format: Mapped[str | None] = mapped_column(Text, nullable=True)
    free_text_raw: Mapped[str | None] = mapped_column(Text, nullable=True)
    free_text_parsed: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    user = relationship("User", backref="business_profiles")
    event = relationship("Event", backref="business_profiles")
    recommendations = relationship(
        "ProjectRecommendation",
        back_populates="profile",
        cascade="all, delete-orphan",
    )
