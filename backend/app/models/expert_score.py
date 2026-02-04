"""Expert Score model for EPIC-013: Expert Scoring.

Stores structured project scores from experts.
"""

import uuid

from sqlalchemy import Boolean, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class ExpertScore(Base):
    """Expert's score for a project."""

    __tablename__ = "expert_scores"

    expert_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("experts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    slot_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("schedule_slots.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Criteria scores (1-3)
    relevance: Mapped[int | None] = mapped_column(Integer, nullable=True)
    practical_value: Mapped[int | None] = mapped_column(Integer, nullable=True)
    novelty: Mapped[int | None] = mapped_column(Integer, nullable=True)
    implementation: Mapped[int | None] = mapped_column(Integer, nullable=True)
    scalability: Mapped[int | None] = mapped_column(Integer, nullable=True)
    research: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Overall impression (1-5)
    overall: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # If student didn't present
    skipped: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    expert = relationship("Expert")
    project = relationship("Project")

    @property
    def total_score(self) -> float | None:
        """Calculate weighted total score."""
        if self.skipped:
            return None
        scores = [
            self.relevance,
            self.practical_value,
            self.novelty,
            self.implementation,
            self.scalability,
            self.research,
        ]
        if not all(s is not None for s in scores):
            return None
        return sum(scores) / len(scores)

    @property
    def is_complete(self) -> bool:
        """Check if all criteria are scored."""
        if self.skipped:
            return True
        return all([
            self.relevance is not None,
            self.practical_value is not None,
            self.novelty is not None,
            self.implementation is not None,
            self.scalability is not None,
            self.research is not None,
            self.overall is not None,
        ])
