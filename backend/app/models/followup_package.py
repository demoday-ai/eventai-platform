"""Follow-up Package model for EPIC-014: Guest Follow-up.

Stores generated follow-up packages for guests after Demo Day.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class FollowupPackage(Base):
    """Follow-up package for a guest after Demo Day."""

    __tablename__ = "followup_packages"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    content: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    sent: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )

    # Relationships
    user = relationship("User")
    event = relationship("Event")

    @property
    def project_count(self) -> int:
        """Number of projects in the package."""
        projects = self.content.get("projects", [])
        return len(projects)

    @property
    def has_contacts(self) -> bool:
        """Check if package has any contact info."""
        projects = self.content.get("projects", [])
        return any(p.get("contact") for p in projects)
