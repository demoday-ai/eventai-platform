"""Shared SQLAlchemy type aliases for cross-dialect models.

Tests run on SQLite (`sqlite+aiosqlite:///:memory:`), production runs on
PostgreSQL with pgvector. JSONType maps to native JSONB on PostgreSQL and
falls back to plain JSON on SQLite.
"""

from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB

JSONType = JSON().with_variant(JSONB(), "postgresql")
