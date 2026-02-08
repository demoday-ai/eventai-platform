"""Celery tasks for async LLM operations.

Each task wraps an async service function to run in Celery's sync worker.
DB engine is initialized once per worker process via Celery signals.
"""

import asyncio
import logging
import uuid
from typing import Any

from celery.signals import worker_process_init, worker_process_shutdown
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.worker.celery_app import celery_app

logger = logging.getLogger(__name__)

# Singleton DB engine — initialized per worker process
_engine = None
_async_session_factory = None


@worker_process_init.connect
def _init_db_engine(**kwargs):
    """Create shared DB engine when worker process starts."""
    global _engine, _async_session_factory
    _engine = create_async_engine(
        settings.database_url,
        echo=False,
        pool_size=3,
        max_overflow=2,
        pool_recycle=600,
        pool_pre_ping=True,
    )
    _async_session_factory = async_sessionmaker(
        _engine, class_=AsyncSession, expire_on_commit=False
    )
    logger.info("Worker DB engine initialized (pool_size=3, max_overflow=2)")


@worker_process_shutdown.connect
def _shutdown_db_engine(**kwargs):
    """Dispose DB engine when worker process shuts down."""
    global _engine, _async_session_factory
    if _engine is not None:
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(_engine.dispose())
        finally:
            loop.close()
        logger.info("Worker DB engine disposed")
    _engine = None
    _async_session_factory = None


def run_async(coro):
    """Run async coroutine in sync Celery task."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


async def _get_session():
    """Get async database session from shared engine."""
    if _async_session_factory is not None:
        return _async_session_factory()
    # Fallback for tests or when signals haven't fired
    engine = create_async_engine(settings.database_url, echo=False)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return factory()


# =============================================================================
# 1. Chat for Profile (onboarding dialog)
# =============================================================================


@celery_app.task(bind=True, max_retries=3, default_retry_delay=5)
def chat_for_profile_task(
    self,
    conversation: list[dict],
    selected_tags: list[str] | None = None,
    role_code: str | None = None,
    guest_subtype: str | None = None,
    custom_subtype: str | None = None,
) -> dict:
    """LLM profiling conversation.

    Returns dict with action ("reply" or "profile") and relevant data.
    """
    from app.services import profiling_service

    async def _run():
        return await profiling_service.chat_for_profile(
            conversation,
            selected_tags,
            role_code=role_code,
            guest_subtype=guest_subtype,
            custom_subtype=custom_subtype,
        )

    try:
        result = run_async(_run())
        logger.info("chat_for_profile_task completed: action=%s", result.get("action"))
        return result
    except Exception as exc:
        logger.exception("chat_for_profile_task failed")
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)


# =============================================================================
# 2. Extract Interests from Text
# =============================================================================


@celery_app.task(bind=True, max_retries=3, default_retry_delay=5)
def extract_interests_from_text_task(
    self,
    raw_text: str,
    available_tags: list[str],
) -> dict:
    """Extract interests/tags from free text using LLM.

    Returns dict with "tags" and "keywords" lists.
    """
    from app.services import profiling_service

    async def _run():
        return await profiling_service.extract_interests_from_text(raw_text, available_tags)

    try:
        result = run_async(_run())
        logger.info(
            "extract_interests_from_text_task completed: tags=%d keywords=%d",
            len(result.get("tags", [])),
            len(result.get("keywords", [])),
        )
        return result
    except Exception as exc:
        logger.exception("extract_interests_from_text_task failed")
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)


# =============================================================================
# 3. Embed Projects (batch embedding for Qdrant)
# =============================================================================


@celery_app.task(bind=True, max_retries=2, default_retry_delay=10)
def embed_projects_task(
    self,
    event_id: str,
) -> dict:
    """Embed all projects for an event into Qdrant vector store.

    Should be called after project import/update.
    Returns dict with count of embedded projects.
    """
    from app.services import embedding_service

    async def _run():
        session = await _get_session()
        try:
            count = await embedding_service.embed_projects(session, uuid.UUID(event_id))
            return {"embedded": count, "event_id": event_id}
        finally:
            await session.close()

    try:
        result = run_async(_run())
        logger.info("embed_projects_task completed: event=%s count=%s", event_id, result.get("embedded"))
        return result
    except Exception as exc:
        logger.exception("embed_projects_task failed")
        raise self.retry(exc=exc, countdown=5 * (self.request.retries + 1))


# =============================================================================
# 4. Generate Recommendations (embedding search + schedule rerank + LLM summaries)
# =============================================================================


@celery_app.task(bind=True, max_retries=2, default_retry_delay=10)
def generate_recommendations_task(
    self,
    user_id: str,
    event_id: str,
) -> dict | None:
    """Generate personalized recommendations for guest profile.

    Pipeline:
    1. Embed profile text (1 API call ~100ms)
    2. Qdrant similarity search (top-30, <10ms)
    3. Schedule-aware rerank (in-memory)
    4. LLM summaries for top-15 (1 LLM call ~3-5s)
    5. Save recommendations to DB

    Returns recommendations dict or None on failure.
    """
    from app.services import profiling_service

    async def _run():
        session = await _get_session()
        try:
            profile = await profiling_service.get_or_create_profile(
                session, uuid.UUID(user_id), uuid.UUID(event_id)
            )
            return await profiling_service.generate_recommendations(session, profile)
        finally:
            await session.close()

    try:
        result = run_async(_run())
        logger.info(
            "generate_recommendations_task completed: user=%s total=%s",
            user_id,
            result.get("total") if result else 0,
        )
        return result
    except Exception as exc:
        logger.exception("generate_recommendations_task failed")
        raise self.retry(exc=exc, countdown=5 * (self.request.retries + 1))


# =============================================================================
# 5. Generate Q&A Questions
# =============================================================================


@celery_app.task(bind=True, max_retries=3, default_retry_delay=5)
def generate_qa_questions_task(
    self,
    user_id: str,
    project_id: str,
) -> list[str]:
    """Generate Q&A questions for a project based on user profile.

    Returns list of question strings.
    """
    from sqlalchemy import select

    from app.models.project import Project
    from app.services import qa_service, user_service

    async def _run():
        session = await _get_session()
        try:
            user = await user_service.get_user_by_id(session, uuid.UUID(user_id))
            if not user:
                return []

            result = await session.execute(
                select(Project).where(Project.id == uuid.UUID(project_id))
            )
            project = result.scalar_one_or_none()
            if not project:
                return []

            guest_profile = await user_service.get_guest_profile(session, user.id)
            business_profile = await user_service.get_business_profile(session, user.id)

            return await qa_service.generate_questions(
                session, user, project, guest_profile, business_profile
            )
        finally:
            await session.close()

    try:
        result = run_async(_run())
        logger.info(
            "generate_qa_questions_task completed: project=%s questions=%d",
            project_id,
            len(result),
        )
        return result
    except Exception as exc:
        logger.exception("generate_qa_questions_task failed")
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)


# =============================================================================
# 6. Generate Comparison Matrix
# =============================================================================


@celery_app.task(bind=True, max_retries=2, default_retry_delay=5)
def generate_comparison_matrix_task(
    self,
    user_id: str,
    project_ids: list[str],
    criteria: list[str],
) -> dict:
    """Generate comparison matrix for selected projects.

    Returns matrix dict or error.
    """
    from sqlalchemy import select

    from app.models.project import Project
    from app.services import qa_service

    async def _run():
        session = await _get_session()
        try:
            result = await session.execute(
                select(Project).where(Project.id.in_([uuid.UUID(pid) for pid in project_ids]))
            )
            projects = list(result.scalars().all())

            if len(projects) < 2:
                return {"error": "Нужно минимум 2 проекта для сравнения"}

            return await qa_service.generate_comparison_matrix(session, projects, criteria)
        finally:
            await session.close()

    try:
        result = run_async(_run())
        logger.info("generate_comparison_matrix_task completed: projects=%d", len(project_ids))
        return result
    except Exception as exc:
        logger.exception("generate_comparison_matrix_task failed")
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)


# =============================================================================
# 7. Cluster Projects
# =============================================================================


@celery_app.task(bind=True, max_retries=1, default_retry_delay=60)
def cluster_projects_task(
    self,
    event_id: str,
    num_rooms: int = 6,
    feedback: str | None = None,
    room_themes: list[str] | None = None,
) -> dict[str, Any]:
    """Run project clustering for an event.

    This is a heavy task (10-60 sec).
    Returns clustering run info or raises exception.
    """
    from app.services import clustering_service

    async def _run():
        session = await _get_session()
        try:
            run = await clustering_service.run_clustering(
                session, uuid.UUID(event_id), num_rooms, feedback, room_themes=room_themes
            )
            # Return serializable dict
            return {
                "run_id": str(run.id),
                "status": run.status,
                "num_rooms": len(run.rooms),
                "rooms": [
                    {
                        "id": str(room.id),
                        "name": room.name,
                        "display_order": room.display_order,
                        "project_count": len(room.project_assignments),
                    }
                    for room in sorted(run.rooms, key=lambda r: r.display_order)
                ],
            }
        finally:
            await session.close()

    try:
        result = run_async(_run())
        logger.info("cluster_projects_task completed: event=%s rooms=%d", event_id, result["num_rooms"])
        return result
    except Exception as exc:
        logger.exception("cluster_projects_task failed")
        raise self.retry(exc=exc, countdown=30)


# =============================================================================
# 8. Run Expert Matching
# =============================================================================


@celery_app.task(bind=True, max_retries=1, default_retry_delay=30)
def run_matching_task(
    self,
    event_id: str,
    use_adjacent_tags: bool = True,
) -> dict[str, Any]:
    """Run expert-room matching for an event.

    Pipeline includes LLM call for adjacent tag resolution.
    Returns matching result dict.
    """
    from app.services import matching_service

    async def _run():
        session = await _get_session()
        try:
            return await matching_service.run_matching(
                session, uuid.UUID(event_id), use_adjacent_tags
            )
        finally:
            await session.close()

    try:
        result = run_async(_run())
        logger.info("run_matching_task completed: event=%s", event_id)
        return result
    except Exception as exc:
        logger.exception("run_matching_task failed")
        raise self.retry(exc=exc, countdown=15)


# =============================================================================
# 9. Agent Chat (VIEW_PROGRAM mode with tools)
# =============================================================================


@celery_app.task(bind=True, max_retries=3, default_retry_delay=5)
def agent_chat_task(
    self,
    system_prompt: str,
    messages: list[dict],
    tools: list[dict],
) -> dict:
    """LLM agent chat with tool calling.

    Returns dict with:
      - "type": "text" | "tool_call"
      - "content": str (if text)
      - "tool_name": str (if tool_call)
      - "tool_args": dict (if tool_call)
    """
    from app.services import llm_client

    async def _run():
        return await llm_client.send_chat_with_tools(
            system_prompt=system_prompt,
            messages=messages,
            tools=tools,
        )

    try:
        result = run_async(_run())
        logger.info("agent_chat_task completed: type=%s", result.get("type"))
        return result
    except Exception as exc:
        logger.exception("agent_chat_task failed")
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)
