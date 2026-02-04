"""Extend guest_subtype_enum: add investor, business_partner, mentor, hr, jury.

Revision ID: 020
Revises: 019
Create Date: 2026-02-04
"""

from alembic import op

revision = "020"
down_revision = "019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE guest_subtype_enum ADD VALUE IF NOT EXISTS 'INVESTOR'")
    op.execute("ALTER TYPE guest_subtype_enum ADD VALUE IF NOT EXISTS 'BUSINESS_PARTNER'")
    op.execute("ALTER TYPE guest_subtype_enum ADD VALUE IF NOT EXISTS 'MENTOR'")
    op.execute("ALTER TYPE guest_subtype_enum ADD VALUE IF NOT EXISTS 'HR'")
    op.execute("ALTER TYPE guest_subtype_enum ADD VALUE IF NOT EXISTS 'JURY'")


def downgrade() -> None:
    # PostgreSQL doesn't support removing enum values directly.
    pass
