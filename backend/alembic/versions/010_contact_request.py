"""Add contact_requests table for EPIC-010.

Revision ID: 010
Revises: 009
Create Date: 2026-02-03
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "contact_requests",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "requester_id",
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
        sa.Column(
            "student_user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("requester_message", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("requester_id", "project_id", name="uq_contact_request_requester_project"),
    )
    op.create_index(
        "ix_contact_requests_requester",
        "contact_requests",
        ["requester_id"],
    )
    op.create_index(
        "ix_contact_requests_student_status",
        "contact_requests",
        ["student_user_id", "status"],
    )


def downgrade() -> None:
    op.drop_index("ix_contact_requests_student_status", table_name="contact_requests")
    op.drop_index("ix_contact_requests_requester", table_name="contact_requests")
    op.drop_table("contact_requests")
