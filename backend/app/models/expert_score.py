"""Bot-side expert scores (bonus-track-llm flow).

Distinct from legacy `expert_scores` (migration 013) used by demoday admin --
this table stores LLM-friendly JSONB criteria scores written when an expert
uses the bot to evaluate projects. Created in migration 038_bonus_tables.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.types import JSONType


class BotExpertScore(Base):
    __tablename__ = "bot_expert_scores"
    __table_args__ = (
        UniqueConstraint("expert_id", "project_id", name="uq_bot_expert_scores_expert_project"),
    )

    expert_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("experts.id", ondelete="CASCADE"),
        nullable=False,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    criteria_scores: Mapped[dict] = mapped_column(JSONType, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
