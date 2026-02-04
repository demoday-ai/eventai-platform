"""Q&A Suggestion model for EPIC-009: Q&A Helper.

Caches LLM-generated questions for guests and business partners.
"""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class QuestionType(str, enum.Enum):
    """Type of questions based on user role and subtype."""

    GUEST_GENERAL = "guest_general"
    GUEST_APPLICANT = "guest_applicant"
    GUEST_STUDENT = "guest_student"
    GUEST_PRACTITIONER = "guest_practitioner"
    BUSINESS_INVESTOR = "business_investor"
    BUSINESS_HR = "business_hr"
    BUSINESS_PARTNER = "business_partner"
    BUSINESS_TECH = "business_tech"


class QASuggestion(Base):
    """Cached Q&A suggestions for a user-project pair."""

    __tablename__ = "qa_suggestions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question_type: Mapped[str] = mapped_column(String(50), nullable=False)
    questions: Mapped[dict] = mapped_column(JSONB, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False
    )

    @property
    def is_expired(self) -> bool:
        """Check if cache has expired."""
        return datetime.now(timezone.utc) > self.expires_at
