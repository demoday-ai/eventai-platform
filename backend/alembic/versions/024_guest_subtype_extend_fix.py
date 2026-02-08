"""Re-add guest_subtype_enum values lost after DB recreation.

Migration 020 added these values, but they were lost when the DB was
recreated via create_all().  IF NOT EXISTS makes this idempotent.

Revision ID: 024
Revises: 023
Create Date: 2026-02-08
"""

from alembic import op

revision = "024"
down_revision = "023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # SQLAlchemy Enum() uses .name for PG native enums (UPPERCASE)
    op.execute("ALTER TYPE guest_subtype_enum ADD VALUE IF NOT EXISTS 'INVESTOR'")
    op.execute("ALTER TYPE guest_subtype_enum ADD VALUE IF NOT EXISTS 'BUSINESS_PARTNER'")
    op.execute("ALTER TYPE guest_subtype_enum ADD VALUE IF NOT EXISTS 'MENTOR'")
    op.execute("ALTER TYPE guest_subtype_enum ADD VALUE IF NOT EXISTS 'HR'")
    op.execute("ALTER TYPE guest_subtype_enum ADD VALUE IF NOT EXISTS 'JURY'")


def downgrade() -> None:
    # PostgreSQL doesn't support removing enum values directly.
    pass
