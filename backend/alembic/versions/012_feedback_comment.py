"""Add feedback_comments table for EPIC-012.

Revision ID: 012
Revises: 011
Create Date: 2026-02-03
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "012"
down_revision = "011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "feedback_comments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "expert_id",
            UUID(as_uuid=True),
            sa.ForeignKey("experts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("original_text", sa.Text, nullable=False),
        sa.Column("processed_text", sa.Text, nullable=True),
        sa.Column("category", sa.String(20), nullable=True),
        sa.Column("is_constructive", sa.Boolean, server_default="true"),
        sa.Column("moderation_status", sa.String(20), server_default="pending"),
        sa.Column("moderator_notes", sa.Text, nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_feedback_comments_project", "feedback_comments", ["project_id"])
    op.create_index(
        "ix_feedback_comments_status",
        "feedback_comments",
        ["moderation_status"],
    )


def downgrade() -> None:
    op.drop_index("ix_feedback_comments_status", table_name="feedback_comments")
    op.drop_index("ix_feedback_comments_project", table_name="feedback_comments")
    op.drop_table("feedback_comments")
