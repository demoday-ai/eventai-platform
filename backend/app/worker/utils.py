"""Utilities for working with Celery tasks from async code."""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any

from celery.result import AsyncResult
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.worker.celery_app import celery_app

logger = logging.getLogger(__name__)

# Singleton DB engine — initialized per worker process (set by tasks.py signals)
_engine = None
_async_session_factory = None


def init_db_engine():
    """Create shared DB engine (called from worker_process_init signal)."""
    global _engine, _async_session_factory
    _engine = create_async_engine(
        settings.database_url,
        echo=False,
        pool_size=3,
        max_overflow=2,
        pool_recycle=600,
        pool_pre_ping=True,
    )
    _async_session_factory = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)
    logger.info("Worker DB engine initialized (pool_size=3, max_overflow=2)")


async def shutdown_db_engine():
    """Dispose DB engine (called from worker_process_shutdown signal)."""
    global _engine, _async_session_factory
    if _engine is not None:
        await _engine.dispose()
        logger.info("Worker DB engine disposed")
    _engine = None
    _async_session_factory = None


# Per-process event loop — reused across all task invocations.
# Creating a new loop per call breaks asyncpg: connections from loop #1
# can't be used in loop #2, causing "Future attached to a different loop".
_worker_loop: asyncio.AbstractEventLoop | None = None


def run_async(coro):
    """Run async coroutine in sync Celery task.

    Reuses a single event loop per worker process so asyncpg connections
    (bound to the loop they were created in) remain valid across retries.
    """
    global _worker_loop
    if _worker_loop is None or _worker_loop.is_closed():
        _worker_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_worker_loop)
    return _worker_loop.run_until_complete(coro)


async def _get_session() -> AsyncSession:
    """Get async database session from shared engine."""
    if _async_session_factory is not None:
        return _async_session_factory()
    # Fallback for tests or when signals haven't fired
    engine = create_async_engine(settings.database_url, echo=False)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return factory()


@asynccontextmanager
async def worker_session():
    """Async context manager for DB session in Celery tasks."""
    session = await _get_session()
    try:
        yield session
    finally:
        await session.close()


DEFAULT_TIMEOUT = 30
SHORT_TIMEOUT = 15


async def wait_for_task(
    task_id: str,
    timeout: float = DEFAULT_TIMEOUT,
    poll_interval: float = 0.5,
) -> tuple[bool, Any]:
    """Wait for Celery task to complete asynchronously.

    Args:
        task_id: Celery task ID
        timeout: Maximum time to wait (seconds)
        poll_interval: How often to check task status (seconds)

    Returns:
        Tuple of (completed: bool, result: Any)
        - If completed=True, result contains the task result
        - If completed=False, result is None (task still running)
    """
    result = AsyncResult(task_id, app=celery_app)
    elapsed = 0.0

    while elapsed < timeout:
        if result.ready():
            if result.successful():
                return True, result.get()
            else:
                logger.warning("Task %s failed: %s", task_id, result.result)
                return True, None
        await asyncio.sleep(poll_interval)
        elapsed += poll_interval

    logger.info("Task %s still running after %.1fs", task_id, timeout)
    return False, None


def get_task_status(task_id: str) -> dict[str, Any]:
    """Get current status of a Celery task (sync).

    Returns dict with:
        - status: "pending", "running", "completed", "failed", "unknown"
        - result: Any (if completed)
        - error: str (if failed)
    """
    result = AsyncResult(task_id, app=celery_app)

    # Map Celery status to normalized values
    celery_status = result.status
    status_map = {
        "PENDING": "pending",
        "STARTED": "running",
        "RETRY": "running",
        "SUCCESS": "completed",
        "FAILURE": "failed",
        "REVOKED": "failed",
    }

    normalized = status_map.get(celery_status, "unknown")

    response = {"status": normalized}

    if result.ready():
        if result.successful():
            response["result"] = result.get()
        else:
            # Get error message
            try:
                exc = result.result
                response["error"] = str(exc) if exc else "Unknown error"
            except Exception:
                response["error"] = "Task failed"

    return response


def revoke_task(task_id: str, terminate: bool = False) -> None:
    """Cancel a pending or running task."""
    celery_app.control.revoke(task_id, terminate=terminate)
    logger.info("Task %s revoked (terminate=%s)", task_id, terminate)
