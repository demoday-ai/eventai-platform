"""Update guest_subtype_enum: add 'student', keep 'applicant' and 'other'.

Revision ID: 016
Revises: 015
Create Date: 2026-02-04
"""

from alembic import op

revision = "016"
down_revision = "015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add 'student' value to the existing enum type
    op.execute("ALTER TYPE guest_subtype_enum ADD VALUE IF NOT EXISTS 'student'")


def downgrade() -> None:
    # PostgreSQL doesn't support removing enum values directly.
    # 'student' value will remain but won't be used.
    pass
