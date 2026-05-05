import importlib

import pytest

DEPENDENCY_MODULES = [
    "fastapi",
    "uvicorn",
    "aiogram",
    "sqlalchemy",
    "asyncpg",
    "alembic",
    "pydantic_settings",
    "jose",
    "httpx",
    "multipart",
    "pytz",
]


@pytest.mark.parametrize("module", DEPENDENCY_MODULES)
def test_runtime_dependency_imports(module):
    importlib.import_module(module)
