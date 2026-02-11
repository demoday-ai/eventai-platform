"""Embedding service for vector-based project recommendations.

Uses OpenRouter embeddings API (google/gemini-embedding-001) and Qdrant for vector search.
"""

import logging
import uuid

import httpx
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, PointStruct, ScoredPoint, VectorParams
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.models.project import Project
from app.models.project_tag import ProjectTag
from app.models.room_project import RoomProject
from app.services.core.llm_client import get_key_manager

logger = logging.getLogger(__name__)

COLLECTION_NAME = "projects"
EMBED_TIMEOUT = 30.0
EMBED_BATCH_SIZE = 50

# Lazy-initialized Qdrant client
_qdrant_client: AsyncQdrantClient | None = None


def _get_qdrant() -> AsyncQdrantClient:
    """Get or create Qdrant async client (singleton)."""
    global _qdrant_client
    if _qdrant_client is None:
        _qdrant_client = AsyncQdrantClient(url=settings.qdrant_url)
        logger.info("Qdrant client initialized: %s", settings.qdrant_url)
    return _qdrant_client


async def _ensure_collection() -> None:
    """Create projects collection if it doesn't exist."""
    client = _get_qdrant()
    collections = await client.get_collections()
    existing = {c.name for c in collections.collections}
    if COLLECTION_NAME not in existing:
        await client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(
                size=settings.embedding_dimensions,
                distance=Distance.COSINE,
            ),
        )
        logger.info("Created Qdrant collection '%s' (dim=%d)", COLLECTION_NAME, settings.embedding_dimensions)


async def embed_text(text: str) -> list[float]:
    """Get embedding vector for text via OpenRouter embeddings API.

    Returns list of floats with length = embedding_dimensions.
    """
    api_key = get_key_manager().get_next_key()
    async with httpx.AsyncClient(timeout=EMBED_TIMEOUT) as client:
        response = await client.post(
            f"{settings.openrouter_base_url}/embeddings",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.embedding_model,
                "input": text,
                "dimensions": settings.embedding_dimensions,
            },
        )
        response.raise_for_status()
        data = response.json()

    get_key_manager().mark_key_success(api_key)
    embedding = data["data"][0]["embedding"]
    return embedding


async def embed_texts_batch(texts: list[str]) -> list[list[float]]:
    """Get embeddings for multiple texts in one API call."""
    if not texts:
        return []

    api_key = get_key_manager().get_next_key()
    async with httpx.AsyncClient(timeout=EMBED_TIMEOUT * 2) as client:
        response = await client.post(
            f"{settings.openrouter_base_url}/embeddings",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.embedding_model,
                "input": texts,
                "dimensions": settings.embedding_dimensions,
            },
        )
        response.raise_for_status()
        data = response.json()

    get_key_manager().mark_key_success(api_key)
    # Sort by index to preserve order
    sorted_data = sorted(data["data"], key=lambda x: x["index"])
    return [item["embedding"] for item in sorted_data]


async def embed_projects(session: AsyncSession, event_id: uuid.UUID) -> int:
    """Embed all projects for an event and upsert into Qdrant.

    Returns number of embedded projects.
    """
    await _ensure_collection()

    # Load projects with tags and room assignments
    result = await session.execute(
        select(Project)
        .where(Project.event_id == event_id)
        .options(
            selectinload(Project.tags).selectinload(ProjectTag.tag),
            selectinload(Project.room_assignments).selectinload(RoomProject.room),
        )
    )
    projects = list(result.scalars().all())

    if not projects:
        logger.info("No projects to embed for event %s", event_id)
        return 0

    # Build texts for embedding
    texts = []
    for p in projects:
        tag_names = [pt.tag.name for pt in p.tags]
        text = f"{p.title}. {p.description}. Теги: {', '.join(tag_names)}"
        texts.append(text)

    # Embed in batches
    all_embeddings: list[list[float]] = []
    for i in range(0, len(texts), EMBED_BATCH_SIZE):
        batch = texts[i : i + EMBED_BATCH_SIZE]
        embeddings = await embed_texts_batch(batch)
        all_embeddings.extend(embeddings)

    # Build Qdrant points
    points = []
    for p, embedding in zip(projects, all_embeddings):
        tag_names = [pt.tag.name for pt in p.tags]
        room_name = None
        room_number = None
        for ra in p.room_assignments:
            room_name = ra.room.name
            room_number = ra.room.display_order + 1
            break

        payload = {
            "event_id": str(event_id),
            "project_id": str(p.id),
            "title": p.title,
            "description": p.description[:500],
            "tags": tag_names,
            "author": p.author,
            "room_name": room_name,
            "room_number": room_number,
        }
        points.append(
            PointStruct(
                id=str(p.id),
                vector=embedding,
                payload=payload,
            )
        )

    # Upsert into Qdrant
    client = _get_qdrant()
    await client.upsert(collection_name=COLLECTION_NAME, points=points)

    logger.info("Embedded %d projects for event %s", len(points), event_id)
    return len(points)


async def find_similar(
    profile_embedding: list[float],
    event_id: uuid.UUID,
    limit: int = 30,
) -> list[ScoredPoint]:
    """Find projects similar to profile embedding using Qdrant vector search.

    Returns list of ScoredPoint with payload containing project info.
    """
    await _ensure_collection()
    client = _get_qdrant()

    from qdrant_client.models import FieldCondition, Filter, MatchValue

    results = await client.search(
        collection_name=COLLECTION_NAME,
        query_vector=profile_embedding,
        query_filter=Filter(must=[FieldCondition(key="event_id", match=MatchValue(value=str(event_id)))]),
        limit=limit,
    )

    return results
