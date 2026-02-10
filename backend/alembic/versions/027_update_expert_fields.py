"""Update expert fields: increase position size and add dd_comments.

Revision ID: 027
Revises: 026
Create Date: 2026-02-10
"""

from alembic import op
import sqlalchemy as sa

revision = "027"
down_revision = "026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Increase position field size from 300 to 500
    op.alter_column(
        "experts",
        "position",
        type_=sa.String(500),
        existing_type=sa.String(300),
        existing_nullable=True,
    )

    # Add dd_comments field
    op.add_column(
        "experts",
        sa.Column("dd_comments", sa.Text, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("experts", "dd_comments")
    op.alter_column(
        "experts",
        "position",
        type_=sa.String(300),
        existing_type=sa.String(500),
        existing_nullable=True,
    )
