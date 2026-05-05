"""Add pgvector extension and bonus columns on projects.

Revision ID: 036_pgvector_projects
Revises: 035_needs_attention
Create Date: 2026-05-03

Adds:
- CREATE EXTENSION vector (requires superuser)
- projects.embedding vector(3072) — Gemini embeddings for pgvector cosine search
- projects.parsed_content jsonb — structured extraction from PPTX/PDF/README artifacts
- projects.tags_json jsonb — denormalized tags for bot retriever (avoids join on project_tags)
- projects.tech_stack_json jsonb — denormalized tech stack for bot retriever

Backfills tags_json/tech_stack_json from existing project_tags relation
and tech_stack string column.
"""

from alembic import op
import sqlalchemy as sa


revision = "036_pgvector_projects"
down_revision = "035_needs_attention"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Enable pgvector extension (requires superuser; idempotent)
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # 2. Add new columns to projects (all nullable, no blocking defaults)
    op.add_column(
        "projects",
        sa.Column("embedding", sa.dialects.postgresql.JSONB(), nullable=True),
    )
    # Switch the column to vector(3072) via raw SQL (alembic doesn't know vector type natively)
    op.execute("ALTER TABLE projects DROP COLUMN embedding")
    op.execute("ALTER TABLE projects ADD COLUMN embedding vector(3072)")

    op.add_column(
        "projects",
        sa.Column("parsed_content", sa.dialects.postgresql.JSONB(), nullable=True),
    )
    op.add_column(
        "projects",
        sa.Column("tags_json", sa.dialects.postgresql.JSONB(), nullable=True),
    )
    op.add_column(
        "projects",
        sa.Column("tech_stack_json", sa.dialects.postgresql.JSONB(), nullable=True),
    )

    # 3. Backfill tags_json from project_tags + tags relation
    op.execute(
        """
        UPDATE projects p SET tags_json = sub.t
        FROM (
            SELECT pt.project_id, jsonb_agg(t.name) AS t
            FROM project_tags pt JOIN tags t ON t.id = pt.tag_id
            GROUP BY pt.project_id
        ) sub
        WHERE p.id = sub.project_id
        """
    )

    # 4. Backfill tech_stack_json from comma-separated tech_stack
    op.execute(
        """
        UPDATE projects
        SET tech_stack_json = to_jsonb(
            string_to_array(regexp_replace(tech_stack, '\\s*,\\s*', ',', 'g'), ',')
        )
        WHERE tech_stack IS NOT NULL AND length(tech_stack) > 0
        """
    )

    # No pgvector index — 330 projects, brute-force <1ms is sufficient.
    # If projects exceed ~1000, add HNSW or IVFFlat index in a later migration.


def downgrade() -> None:
    op.drop_column("projects", "tech_stack_json")
    op.drop_column("projects", "tags_json")
    op.drop_column("projects", "parsed_content")
    op.execute("ALTER TABLE projects DROP COLUMN IF EXISTS embedding")
    # Do NOT drop vector extension — other tables/services may depend on it.
