"""Monitoring and health check endpoints."""

import logging

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/monitoring", tags=["Monitoring"])


@router.get("/llm/health")
async def llm_health(user: User = Depends(get_current_user)):
    """Check health of all LLM API keys.

    Returns status of each configured API key.
    Requires authentication.
    """
    from app.services.llm_client import check_api_health

    return await check_api_health()


@router.get("/llm/stats")
async def llm_stats(user: User = Depends(get_current_user)):
    """Get statistics about LLM API key usage.

    Returns availability and failure counts for each key.
    Requires authentication.
    """
    from app.services.llm_client import get_key_manager

    return get_key_manager().get_stats()


@router.get("/services")
async def services_status():
    """Get links and status of all infrastructure services.

    Returns URLs and basic status for monitoring.
    """
    from app.config import settings

    domain = "team12.camp.aitalenthub.ru"

    services = {
        "rabbitmq": {
            "management_ui": f"https://{domain}/rabbitmq/",
            "local_ui": "http://localhost:15672",
            "credentials": "demoday/demoday",
        },
        "flower": {
            "ui": f"https://{domain}/flower/",
            "description": "Celery worker monitoring",
            "credentials": "demoday/demoday",
        },
        "redis": {
            "url": settings.redis_url,
            "note": "Use redis-cli to connect",
        },
        "database": {
            "url": settings.database_url.replace(settings.database_url.split("@")[0].split("://")[1], "***"),
            "note": "PostgreSQL 16",
        },
        "celery": {
            "broker": "RabbitMQ",
            "backend": "Redis",
            "monitor": f"https://{domain}/flower/",
        },
    }

    return {
        "services": services,
        "links": {
            "rabbitmq": f"https://{domain}/rabbitmq/",
            "flower": f"https://{domain}/flower/",
            "api_docs": f"https://{domain}/docs",
            "admin": f"https://{domain}/",
        },
    }


@router.get("/celery/stats")
async def celery_stats(user: User = Depends(get_current_user)):
    """Get Celery worker statistics.

    Requires authentication.
    """
    try:
        from app.worker.celery_app import celery_app

        # Get active workers
        inspect = celery_app.control.inspect()
        active = inspect.active() or {}
        stats = inspect.stats() or {}

        return {
            "workers": list(active.keys()),
            "active_tasks": {k: len(v) for k, v in active.items()},
            "stats": stats,
        }
    except Exception as e:
        logger.exception("Failed to get Celery stats")
        return {
            "error": str(e),
            "workers": [],
        }
