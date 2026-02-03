"""Add qa_suggestions table for EPIC-009.

Revision ID: 009
Revises: 008
Create Date: 2026-02-03
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "qa_suggestions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "project_id",
            UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("question_type", sa.String(50), nullable=False),
        sa.Column("questions", JSONB, nullable=False),
        sa.Column(
            "generated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_qa_suggestions_user_project",
        "qa_suggestions",
        ["user_id", "project_id"],
    )
    op.create_index(
        "ix_qa_suggestions_expires",
        "qa_suggestions",
        ["expires_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_qa_suggestions_expires", table_name="qa_suggestions")
    op.drop_index("ix_qa_suggestions_user_project", table_name="qa_suggestions")
    op.drop_table("qa_suggestions")
