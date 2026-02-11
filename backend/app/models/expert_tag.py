import uuid

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class ExpertTag(Base):
    __tablename__ = "expert_tags"
    __table_args__ = (UniqueConstraint("expert_id", "tag_id", name="uq_expert_tags_expert_tag"),)

    expert_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("experts.id", ondelete="CASCADE"), nullable=False
    )
    tag_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tags.id", ondelete="CASCADE"), nullable=False
    )

    expert = relationship("Expert", back_populates="tags")
    tag = relationship("Tag")
