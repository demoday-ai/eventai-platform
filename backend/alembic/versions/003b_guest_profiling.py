"""Guest profiling tables.

Revision ID: 004
Revises: 003
Create Date: 2026-02-02
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "003b"
down_revision = "003a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. guest_profiles
    op.create_table(
        "guest_profiles",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "event_id",
            UUID(as_uuid=True),
            sa.ForeignKey("events.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("selected_tags", JSONB, nullable=False, server_default="[]"),
        sa.Column("extracted_tags", JSONB, nullable=False, server_default="[]"),
        sa.Column("keywords", JSONB, nullable=False, server_default="[]"),
        sa.Column("raw_text", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("user_id", "event_id", name="uq_guest_profiles_user_event"),
    )
    op.create_index("ix_guest_profiles_event_id", "guest_profiles", ["event_id"])

    # 2. recommendations
    op.create_table(
        "recommendations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "guest_profile_id",
            UUID(as_uuid=True),
            sa.ForeignKey("guest_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "project_id",
            UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("relevance_score", sa.Float, nullable=False),
        sa.Column("category", sa.String(20), nullable=False),
        sa.Column("rank", sa.Integer, nullable=False),
        sa.Column("llm_summary", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "guest_profile_id", "project_id", name="uq_recommendations_profile_project"
        ),
    )
    op.create_index(
        "ix_recommendations_guest_profile_id", "recommendations", ["guest_profile_id"]
    )


def downgrade() -> None:
    op.drop_table("recommendations")
    op.drop_table("guest_profiles")
