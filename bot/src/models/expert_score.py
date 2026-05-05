from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base


# 031-bot-replacement: legacy demoday `expert_scores` (migration 013) is
# admin-owned with a different schema. Bonus bot writes here instead.
class ExpertScore(Base):
    __tablename__ = "bot_expert_scores"
    __table_args__ = (
        UniqueConstraint("expert_id", "project_id", name="uq_bot_expert_scores_expert_project"),
    )

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )
    expert_id: Mapped[UUID] = mapped_column(ForeignKey("experts.id"))
    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id"))
    criteria_scores: Mapped[dict] = mapped_column(JSONB)
    comment: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        default=None,
        onupdate=func.now(),
    )
