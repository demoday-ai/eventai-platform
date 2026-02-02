"""Participation requests for student schedule acknowledgment.

Revision ID: 005
Revises: 004
Create Date: 2026-02-02
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM, UUID

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enum type only if it doesn't exist
    op.execute(sa.text(
        "DO $$ BEGIN "
        "CREATE TYPE participation_status_enum AS ENUM ('pending', 'sent', 'acknowledged'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; "
        "END $$"
    ))

    # Use postgresql.ENUM with create_type=False to avoid duplicate creation
    participation_status = ENUM(
        "pending", "sent", "acknowledged",
        name="participation_status_enum",
        create_type=False,
    )

    op.create_table(
        "participation_requests",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
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
        sa.Column(
            "room_project_id",
            UUID(as_uuid=True),
            sa.ForeignKey("room_projects.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "status",
            participation_status,
            nullable=False,
            server_default="pending",
        ),
        sa.Column("reminder_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("escalated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("telegram_message_id", sa.BigInteger, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "event_id", "project_id", name="uq_participation_event_project"
        ),
    )
    op.create_index(
        "ix_participation_requests_event_status",
        "participation_requests",
        ["event_id", "status"],
    )
    op.create_index(
        "ix_participation_requests_user",
        "participation_requests",
        ["user_id"],
    )


def downgrade() -> None:
    op.drop_table("participation_requests")
    op.execute(sa.text("DROP TYPE IF EXISTS participation_status_enum"))
