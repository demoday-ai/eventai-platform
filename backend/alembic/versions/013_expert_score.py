"""Add expert_scores table for EPIC-013.

Revision ID: 013
Revises: 012
Create Date: 2026-02-03
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "013"
down_revision = "012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "expert_scores",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "expert_id",
            UUID(as_uuid=True),
            sa.ForeignKey("experts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "project_id",
            UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "slot_id",
            UUID(as_uuid=True),
            sa.ForeignKey("schedule_slots.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("relevance", sa.Integer, nullable=True),
        sa.Column("practical_value", sa.Integer, nullable=True),
        sa.Column("novelty", sa.Integer, nullable=True),
        sa.Column("implementation", sa.Integer, nullable=True),
        sa.Column("scalability", sa.Integer, nullable=True),
        sa.Column("research", sa.Integer, nullable=True),
        sa.Column("overall", sa.Integer, nullable=True),
        sa.Column("skipped", sa.Boolean, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("expert_id", "project_id", name="uq_expert_score_expert_project"),
    )
    op.create_index("ix_expert_scores_expert", "expert_scores", ["expert_id"])
    op.create_index("ix_expert_scores_project", "expert_scores", ["project_id"])


def downgrade() -> None:
    op.drop_index("ix_expert_scores_project", table_name="expert_scores")
    op.drop_index("ix_expert_scores_expert", table_name="expert_scores")
    op.drop_table("expert_scores")
