"""Add business_profiles and project_recommendations tables.

Revision ID: 003
Revises: 002
Create Date: 2026-02-02
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create business_objective enum
    op.execute("""
        CREATE TYPE business_objective AS ENUM
        ('investment', 'hiring', 'technology', 'partnership')
    """)

    # Create business_profiles table
    op.create_table(
        "business_profiles",
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
            "objective",
            sa.Enum(
                "investment", "hiring", "technology", "partnership",
                name="business_objective",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("industries", ARRAY(sa.Text), nullable=True),
        sa.Column("tech_stack", ARRAY(sa.Text), nullable=True),
        sa.Column("project_stages", ARRAY(sa.Text), nullable=True),
        sa.Column("collaboration_format", sa.Text, nullable=True),
        sa.Column("free_text_raw", sa.Text, nullable=True),
        sa.Column("free_text_parsed", JSONB, nullable=True),
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
        sa.UniqueConstraint("user_id", "event_id", name="uq_business_profiles_user_event"),
    )

    # Create project_recommendations table
    op.create_table(
        "project_recommendations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "profile_id",
            UUID(as_uuid=True),
            sa.ForeignKey("business_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "project_id",
            UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("relevance_score", sa.Integer, nullable=False),
        sa.Column("relevance_explanation", sa.Text, nullable=True),
        sa.Column("rank", sa.Integer, nullable=False),
        sa.Column("is_bookmarked", sa.Boolean, nullable=False, default=False),
        sa.Column("is_viewed", sa.Boolean, nullable=False, default=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "profile_id", "project_id", name="uq_recommendations_profile_project"
        ),
    )
    op.create_index(
        "ix_recommendations_profile_rank",
        "project_recommendations",
        ["profile_id", "rank"],
    )


def downgrade() -> None:
    op.drop_index("ix_recommendations_profile_rank", table_name="project_recommendations")
    op.drop_table("project_recommendations")
    op.drop_table("business_profiles")
    op.execute("DROP TYPE IF EXISTS business_objective")
