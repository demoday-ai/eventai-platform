"""Add business_followups table for EPIC-015.

Revision ID: 015
Revises: 014
Create Date: 2026-02-03
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "015"
down_revision = "014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enum type
    pipeline_status = sa.Enum(
        "interested", "contacted", "negotiating", "closed_won", "closed_lost",
        name="pipelinestatus"
    )
    pipeline_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "business_followups",
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
            "project_id",
            UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", pipeline_status, server_default="interested"),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("loi_generated", sa.Boolean, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("user_id", "project_id", name="uq_business_followup_user_project"),
    )
    op.create_index("ix_business_followups_user", "business_followups", ["user_id"])
    op.create_index("ix_business_followups_event", "business_followups", ["event_id"])
    op.create_index("ix_business_followups_project", "business_followups", ["project_id"])


def downgrade() -> None:
    op.drop_index("ix_business_followups_project", table_name="business_followups")
    op.drop_index("ix_business_followups_event", table_name="business_followups")
    op.drop_index("ix_business_followups_user", table_name="business_followups")
    op.drop_table("business_followups")

    # Drop enum type
    sa.Enum(name="pipelinestatus").drop(op.get_bind(), checkfirst=True)
