from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base


class Recommendation(Base):
    __tablename__ = "recommendations"
    __table_args__ = (
        UniqueConstraint("guest_profile_id", "project_id"),
    )

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )
    # 031-bot-replacement: renamed from profile_id to match demoday schema.
    guest_profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("guest_profiles.id"),
        index=True,
    )
    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id"))
    relevance_score: Mapped[float] = mapped_column(Float)
    # DB column is varchar(20). Keep model wider but values stay short ('must_visit', 'if_time').
    category: Mapped[str] = mapped_column(String(32))
    rank: Mapped[int] = mapped_column(Integer)
    # Optional LLM-generated short reason "почему этот проект в топе". Stored by tools/get_summary.
    llm_summary: Mapped[str | None] = mapped_column(Text, default=None)
    slot_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("schedule_slots.id"),
        default=None,
    )
    visit_order: Mapped[int | None] = mapped_column(Integer, default=None)
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
    )
