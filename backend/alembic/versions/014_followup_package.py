"""Add followup_packages table for EPIC-014.

Revision ID: 014
Revises: 013
Create Date: 2026-02-03
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON

revision = "014"
down_revision = "013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "followup_packages",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "event_id",
            UUID(as_uuid=True),
            sa.ForeignKey("events.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "generated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("content", JSON, nullable=False),
        sa.Column("sent", sa.Boolean, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_followup_packages_user", "followup_packages", ["user_id"])
    op.create_index("ix_followup_packages_event", "followup_packages", ["event_id"])


def downgrade() -> None:
    op.drop_index("ix_followup_packages_event", table_name="followup_packages")
    op.drop_index("ix_followup_packages_user", table_name="followup_packages")
    op.drop_table("followup_packages")
