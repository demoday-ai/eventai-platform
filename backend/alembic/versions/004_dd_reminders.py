"""DD Reminders - schedule slots, notifications, schedule change logs.

Revision ID: 004
Revises: 003
Create Date: 2026-02-02

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "004"
down_revision = "003b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add schedule_approved_at to clustering_runs
    op.add_column(
        "clustering_runs",
        sa.Column("schedule_approved_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Create schedule_slots table
    op.create_table(
        "schedule_slots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("room_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clustering_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False, default=0),
        sa.Column("status", sa.String(20), nullable=False, default="scheduled"),
        sa.Column("status_changed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["room_id"], ["rooms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["clustering_run_id"], ["clustering_runs.id"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint("project_id", "clustering_run_id", name="uq_slot_project_run"),
    )

    op.create_index("ix_schedule_slots_event_id", "schedule_slots", ["event_id"])
    op.create_index("ix_schedule_slots_room_id", "schedule_slots", ["room_id"])
    op.create_index("ix_schedule_slots_project_id", "schedule_slots", ["project_id"])
    op.create_index("ix_schedule_slots_start_time", "schedule_slots", ["start_time"])
    op.create_index("ix_schedule_slots_status", "schedule_slots", ["status"])

    # Create notifications table
    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("schedule_slot_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("type", sa.String(30), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, default="pending"),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, default=0),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("batch_key", sa.String(100), nullable=True),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["schedule_slot_id"], ["schedule_slots.id"], ondelete="SET NULL"
        ),
    )

    op.create_index("ix_notifications_event_id", "notifications", ["event_id"])
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])
    op.create_index("ix_notifications_type", "notifications", ["type"])
    op.create_index("ix_notifications_status", "notifications", ["status"])
    op.create_index("ix_notifications_scheduled_at", "notifications", ["scheduled_at"])

    # Partial unique index for deduplication
    op.execute(
        """
        CREATE UNIQUE INDEX ix_notifications_dedup
        ON notifications (user_id, schedule_slot_id, type)
        WHERE status NOT IN ('failed', 'cancelled', 'batched')
        """
    )

    # Create schedule_change_logs table
    op.create_table(
        "schedule_change_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("schedule_slot_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("changed_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("change_type", sa.String(30), nullable=False),
        sa.Column("old_start_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("old_end_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("old_room_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("new_start_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("new_end_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("new_room_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("notifications_sent", sa.Boolean(), nullable=False, default=False),
        sa.ForeignKeyConstraint(
            ["schedule_slot_id"], ["schedule_slots.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["changed_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["old_room_id"], ["rooms.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["new_room_id"], ["rooms.id"], ondelete="SET NULL"),
    )

    op.create_index(
        "ix_schedule_change_logs_slot_id", "schedule_change_logs", ["schedule_slot_id"]
    )
    op.create_index(
        "ix_schedule_change_logs_event_id", "schedule_change_logs", ["event_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_schedule_change_logs_event_id", "schedule_change_logs")
    op.drop_index("ix_schedule_change_logs_slot_id", "schedule_change_logs")
    op.drop_table("schedule_change_logs")

    op.execute("DROP INDEX IF EXISTS ix_notifications_dedup")
    op.drop_index("ix_notifications_scheduled_at", "notifications")
    op.drop_index("ix_notifications_status", "notifications")
    op.drop_index("ix_notifications_type", "notifications")
    op.drop_index("ix_notifications_user_id", "notifications")
    op.drop_index("ix_notifications_event_id", "notifications")
    op.drop_table("notifications")

    op.drop_index("ix_schedule_slots_status", "schedule_slots")
    op.drop_index("ix_schedule_slots_start_time", "schedule_slots")
    op.drop_index("ix_schedule_slots_project_id", "schedule_slots")
    op.drop_index("ix_schedule_slots_room_id", "schedule_slots")
    op.drop_index("ix_schedule_slots_event_id", "schedule_slots")
    op.drop_table("schedule_slots")

    op.drop_column("clustering_runs", "schedule_approved_at")
