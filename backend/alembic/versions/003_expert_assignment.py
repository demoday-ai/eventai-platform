"""Expert assignment tables.

Revision ID: 003
Revises: 002
Create Date: 2026-02-02
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. experts (FK -> users, events)
    op.create_table(
        "experts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("seed_id", sa.String(20), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("telegram_username", sa.String(100), nullable=True),
        sa.Column("position", sa.String(300), nullable=True),
        sa.Column("inviter", sa.String(100), nullable=True),
        sa.Column("dd_status_seed", sa.String(50), nullable=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, unique=True),
        sa.Column("event_id", UUID(as_uuid=True), sa.ForeignKey("events.id", ondelete="CASCADE"), nullable=False),
        sa.Column("bot_started", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("bot_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("seed_id", "event_id", name="uq_experts_seed_event"),
    )
    op.create_index("ix_experts_telegram_username", "experts", ["telegram_username"])
    op.create_index("ix_experts_seed_id", "experts", ["seed_id"])

    # 2. expert_tags (FK -> experts, tags)
    op.create_table(
        "expert_tags",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("expert_id", UUID(as_uuid=True), sa.ForeignKey("experts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tag_id", UUID(as_uuid=True), sa.ForeignKey("tags.id", ondelete="CASCADE"), nullable=False),
        sa.UniqueConstraint("expert_id", "tag_id", name="uq_expert_tags_expert_tag"),
    )

    # 3. expert_room_assignments (FK -> experts, rooms, clustering_runs)
    op.create_table(
        "expert_room_assignments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expert_id", UUID(as_uuid=True), sa.ForeignKey("experts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("room_id", UUID(as_uuid=True), sa.ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False),
        sa.Column("clustering_run_id", UUID(as_uuid=True), sa.ForeignKey("clustering_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("match_score", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("is_manual", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("status", sa.String(20), nullable=False, server_default="proposed"),
        sa.Column("status_changed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("invite_viewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reminder_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("last_reminder_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("expert_id", "clustering_run_id", name="uq_era_expert_clustering_run"),
    )
    op.create_index("ix_era_clustering_run_id", "expert_room_assignments", ["clustering_run_id"])
    op.create_index("ix_era_room_id", "expert_room_assignments", ["room_id"])
    op.create_index("ix_era_status", "expert_room_assignments", ["status"])

    # 4. escalations (FK -> experts, rooms, events)
    op.create_table(
        "escalations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("expert_id", UUID(as_uuid=True), sa.ForeignKey("experts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("room_id", UUID(as_uuid=True), sa.ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_id", UUID(as_uuid=True), sa.ForeignKey("events.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type", sa.String(30), nullable=False),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column("resolved", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_escalations_event_id", "escalations", ["event_id"])
    op.create_index("ix_escalations_resolved", "escalations", ["resolved"])


def downgrade() -> None:
    op.drop_table("escalations")
    op.drop_table("expert_room_assignments")
    op.drop_table("expert_tags")
    op.drop_table("experts")
