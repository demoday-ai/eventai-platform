import os
from pathlib import Path

import pytest

from alembic import command
from alembic.config import Config


@pytest.mark.integration
def test_alembic_upgrade_clean_db():
    db_url = os.getenv("MIGRATION_TEST_DATABASE_URL")
    if not db_url:
        pytest.skip("MIGRATION_TEST_DATABASE_URL not set")

    repo_root = Path(__file__).resolve().parents[1]
    alembic_ini = repo_root / "alembic.ini"
    config = Config(str(alembic_ini))
    config.set_main_option("sqlalchemy.url", db_url)

    command.upgrade(config, "head")
