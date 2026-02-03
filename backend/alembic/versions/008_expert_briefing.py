"""Add expert_briefings table for EPIC-008.

Revision ID: 008
Revises: 007
Create Date: 2026-02-03
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM, UUID

revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enum type
    op.execute(sa.text(
        "DO $$ BEGIN "
        "CREATE TYPE briefing_status_enum AS ENUM ('pending', 'sent', 'failed', 'skipped'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; "
        "END $$"
    ))

    briefing_status = ENUM(
        "pending", "sent", "failed", "skipped",
        name="briefing_status_enum",
        create_type=False,
    )

    op.create_table(
        "expert_briefings",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "expert_id",
            UUID(as_uuid=True),
            sa.ForeignKey("experts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "room_id",
            UUID(as_uuid=True),
            sa.ForeignKey("rooms.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "event_id",
            UUID(as_uuid=True),
            sa.ForeignKey("events.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", briefing_status, nullable=False, server_default="pending"),
        sa.Column("project_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("message_count", sa.Integer, nullable=False, server_default="1"),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.String(500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_expert_briefings_expert_id", "expert_briefings", ["expert_id"])
    op.create_index("ix_expert_briefings_event_id", "expert_briefings", ["event_id"])

    # Add project fields for briefing cards
    op.add_column("projects", sa.Column("github_url", sa.String(500), nullable=True))
    op.add_column("projects", sa.Column("tech_stack", sa.String(500), nullable=True))
    op.add_column("projects", sa.Column("presentation_url", sa.String(500), nullable=True))
    op.add_column("projects", sa.Column("demo_url", sa.String(500), nullable=True))


def downgrade() -> None:
    op.drop_column("projects", "demo_url")
    op.drop_column("projects", "presentation_url")
    op.drop_column("projects", "tech_stack")
    op.drop_column("projects", "github_url")
    op.drop_table("expert_briefings")
    op.execute(sa.text("DROP TYPE IF EXISTS briefing_status_enum"))
