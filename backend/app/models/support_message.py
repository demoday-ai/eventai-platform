from uuid import UUID

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class SupportMessage(Base):
    __tablename__ = "support_messages"

    thread_id: Mapped[UUID] = mapped_column(ForeignKey("support_threads.id"), nullable=False, index=True)
    sender_type: Mapped[str] = mapped_column(String(20), nullable=False)  # "user" | "organizer"
    sender_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)

    thread = relationship("SupportThread", back_populates="messages")
    sender = relationship("User", lazy="selectin")
