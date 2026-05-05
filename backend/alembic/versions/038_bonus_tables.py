"""Add bonus-track-llm tables and ALTER existing for bot agent.

Revision ID: 038_bonus_tables
Revises: 037_user_role_code
Create Date: 2026-05-03

Creates new tables for bonus-track-llm bot:
- chat_messages — agent dialog log (user + assistant turns)
- support_log    — bot support requests (correlation_id, organizer answer)
- expert_scores  — bot-side expert scoring (1-5 per criterion)

ALTERs existing tables to add bonus-required fields:
- guest_profiles: + nl_summary, company, position, objective, business_objectives
- recommendations: + slot_id, visit_order
- experts: + invite_code, tags_json
- business_followups.status: enum -> varchar(64) to accept both demoday
  (interested|contacted|negotiating|closed_won|closed_lost) and bonus
  (interested|contacted|meeting_scheduled|rejected|in_progress) values.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID


revision = "038_bonus_tables"
down_revision = "037_user_role_code"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ============================================================
    # 1. ALTER guest_profiles
    # ============================================================
    op.add_column("guest_profiles", sa.Column("nl_summary", sa.Text(), nullable=True))
    op.add_column("guest_profiles", sa.Column("company", sa.String(255), nullable=True))
    op.add_column("guest_profiles", sa.Column("position", sa.String(255), nullable=True))
    op.add_column("guest_profiles", sa.Column("objective", sa.Text(), nullable=True))
    op.add_column("guest_profiles", sa.Column("business_objectives", JSONB, nullable=True))

    # ============================================================
    # 2. ALTER recommendations
    # ============================================================
    op.add_column(
        "recommendations",
        sa.Column(
            "slot_id",
            UUID(as_uuid=True),
            sa.ForeignKey("schedule_slots.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column("recommendations", sa.Column("visit_order", sa.Integer(), nullable=True))

    # ============================================================
    # 3. ALTER experts
    # ============================================================
    op.add_column("experts", sa.Column("invite_code", sa.String(128), nullable=True))
    op.add_column("experts", sa.Column("tags_json", JSONB, nullable=True))
    # bonus bot expert flow keeps a single room reference per expert directly on
    # the row; legacy admin path keeps the richer `expert_room_assignment` table
    # untouched.
    op.add_column(
        "experts",
        sa.Column(
            "room_id",
            UUID(as_uuid=True),
            sa.ForeignKey("rooms.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "uq_experts_invite_code", "experts", ["invite_code"], unique=True,
        postgresql_where=sa.text("invite_code IS NOT NULL"),
    )

    # ============================================================
    # 4. ALTER business_followups.status: enum -> varchar(64)
    #    (allow both demoday and bonus status values)
    # ============================================================
    op.execute(
        "ALTER TABLE business_followups ALTER COLUMN status TYPE varchar(64) "
        "USING status::text"
    )
    op.execute(
        "ALTER TABLE business_followups ALTER COLUMN status SET DEFAULT 'interested'"
    )
    # Drop old enum if no other tables reference it
    op.execute("DROP TYPE IF EXISTS pipelinestatus")

    # ============================================================
    # 5. CREATE chat_messages
    # ============================================================
    op.create_table(
        "chat_messages",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_id", UUID(as_uuid=True), sa.ForeignKey("events.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("idx_chat_messages_user_id", "chat_messages", ["user_id"])

    # ============================================================
    # 6. CREATE support_log
    # ============================================================
    op.create_table(
        "support_log",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_id", UUID(as_uuid=True), sa.ForeignKey("events.id", ondelete="CASCADE"), nullable=False),
        sa.Column("correlation_id", sa.String(64), nullable=False, unique=True),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("answered_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("idx_support_log_user_id", "support_log", ["user_id"])
    op.create_index("idx_support_log_correlation_id", "support_log", ["correlation_id"])

    # ============================================================
    # 7. CREATE bot_expert_scores
    # NOTE: legacy `expert_scores` (migration 013) keeps demoday admin scoring;
    # bonus bot stores its own JSONB criteria scores in a separate table to avoid
    # schema drift between two flows.
    # ============================================================
    op.create_table(
        "bot_expert_scores",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("expert_id", UUID(as_uuid=True), sa.ForeignKey("experts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("criteria_scores", JSONB, nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("expert_id", "project_id", name="uq_bot_expert_scores_expert_project"),
    )


def downgrade() -> None:
    op.drop_table("bot_expert_scores")
    op.drop_index("idx_support_log_correlation_id", table_name="support_log")
    op.drop_index("idx_support_log_user_id", table_name="support_log")
    op.drop_table("support_log")
    op.drop_index("idx_chat_messages_user_id", table_name="chat_messages")
    op.drop_table("chat_messages")

    # business_followups.status: varchar -> enum is destructive; leave as varchar.
    # (Recreating the enum would require validating all existing values.)

    op.drop_index("uq_experts_invite_code", table_name="experts")
    op.drop_column("experts", "room_id")
    op.drop_column("experts", "tags_json")
    op.drop_column("experts", "invite_code")

    op.drop_column("recommendations", "visit_order")
    op.drop_column("recommendations", "slot_id")

    op.drop_column("guest_profiles", "business_objectives")
    op.drop_column("guest_profiles", "objective")
    op.drop_column("guest_profiles", "position")
    op.drop_column("guest_profiles", "company")
    op.drop_column("guest_profiles", "nl_summary")
