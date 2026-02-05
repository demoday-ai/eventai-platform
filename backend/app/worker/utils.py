"""Utilities for working with Celery tasks from async code."""

import asyncio
import logging
from typing import Any

from celery.result import AsyncResult

from app.worker.celery_app import celery_app

logger = logging.getLogger(__name__)

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
