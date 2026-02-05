"""Simple in-memory background job system."""

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Job:
    id: str
    job_type: str | None = None
    status: JobStatus = JobStatus.PENDING
    result: Any = None
    error: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None


# In-memory job store (for single-instance deployment)
_jobs: dict[str, Job] = {}
# Track active jobs by type to prevent duplicates
_active_jobs_by_type: dict[str, str] = {}  # type -> job_id


def create_job(job_type: str | None = None) -> Job:
    """Create a new job and return it."""
    job_id = str(uuid.uuid4())
    job = Job(id=job_id, job_type=job_type)
    _jobs[job_id] = job
    if job_type:
        _active_jobs_by_type[job_type] = job_id
    return job


def get_job(job_id: str) -> Job | None:
    """Get job by ID."""
    return _jobs.get(job_id)


def get_active_job_by_type(job_type: str) -> Job | None:
    """Get active (pending/running) job by type."""
    job_id = _active_jobs_by_type.get(job_type)
    if job_id:
        job = _jobs.get(job_id)
        if job and job.status in (JobStatus.PENDING, JobStatus.RUNNING):
            return job
        # Job completed or failed, clean up
        del _active_jobs_by_type[job_type]
    return None


def update_job(job_id: str, status: JobStatus, result: Any = None, error: str | None = None) -> None:
    """Update job status."""
    job = _jobs.get(job_id)
    if job:
        job.status = status
        job.result = result
        job.error = error
        if status in (JobStatus.COMPLETED, JobStatus.FAILED):
            job.completed_at = datetime.now(timezone.utc)
            # Clean up active job tracking
            if job.job_type and _active_jobs_by_type.get(job.job_type) == job_id:
                del _active_jobs_by_type[job.job_type]


async def run_in_background(job_id: str, coro) -> None:
    """Run a coroutine in the background and update job status."""
    update_job(job_id, JobStatus.RUNNING)
    try:
        result = await coro
        update_job(job_id, JobStatus.COMPLETED, result=result)
        logger.info(f"Job {job_id} completed successfully")
    except Exception as e:
        logger.exception(f"Job {job_id} failed: {e}")
        update_job(job_id, JobStatus.FAILED, error=str(e))


def start_background_job(coro, job_type: str | None = None) -> Job:
    """Create a job and start running the coroutine in background.

    If job_type is provided, prevents starting duplicate jobs of the same type.
    """
    job = create_job(job_type=job_type)
    asyncio.create_task(run_in_background(job.id, coro))
    return job


# Cleanup old jobs periodically (simple implementation)
def cleanup_old_jobs(max_age_hours: int = 24) -> int:
    """Remove jobs older than max_age_hours. Returns count of removed jobs."""
    now = datetime.now(timezone.utc)
    to_remove = []
    for job_id, job in _jobs.items():
        age = (now - job.created_at).total_seconds() / 3600
        if age > max_age_hours:
            to_remove.append(job_id)
    for job_id in to_remove:
        del _jobs[job_id]
    return len(to_remove)
