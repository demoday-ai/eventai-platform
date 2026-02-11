"""Contact Request model for EPIC-010: Contact Requests.

Manages contact exchange requests between users and project authors.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class ContactRequestStatus(str, enum.Enum):
    """Status of a contact request."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class ContactRequest(Base):
    """Request to exchange contact with a project author."""

    __tablename__ = "contact_requests"
    __table_args__ = (UniqueConstraint("requester_id", "project_id", name="uq_contact_request_requester_project"),)

    requester_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    student_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=ContactRequestStatus.PENDING.value,
    )
    requester_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    responded_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Relationships
    requester = relationship("User", foreign_keys=[requester_id])
    student = relationship("User", foreign_keys=[student_user_id])
    project = relationship("Project")

    @property
    def is_pending(self) -> bool:
        return self.status == ContactRequestStatus.PENDING.value
