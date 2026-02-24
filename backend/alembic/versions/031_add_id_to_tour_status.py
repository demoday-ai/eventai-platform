"""add id column to admin_tour_status

Revision ID: 031
Revises: 030
Create Date: 2026-02-24

AdminTourStatus inherits from Base which defines `id: Mapped[UUID]` as a
primary key column.  SQLAlchemy therefore includes admin_tour_status.id in
every SELECT it generates for this model.  The original migration (030) did
not add this column, causing UndefinedColumnError at runtime.

This migration adds the missing id column with a server-side default so that
existing rows and future inserts are handled automatically.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = "031"
down_revision: Union[str, None] = "030"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "admin_tour_status",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("admin_tour_status", "id")
