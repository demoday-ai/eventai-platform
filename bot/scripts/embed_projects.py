#!/usr/bin/env python3
"""Generate pgvector embeddings for all projects with embedding IS NULL.

One-shot data op. Costs ~$1-2 via OpenRouter Gemini embeddings, ~10 min for 294 projects.
Idempotent: skips projects that already have embeddings.

Usage (inside bot container):
    docker compose exec bot python -m scripts.embed_projects
"""
import asyncio
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

os.environ.setdefault("BOT_TOKEN", "embed")

import httpx
from sqlalchemy import select, text as sql_text

from src.core.config import settings
from src.core.database import async_session
from src.models.project import Project

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger(__name__)


async def main() -> None:
    api_key = os.environ.get("OPENROUTER_API_KEY", settings.openrouter_api_key)
    if not api_key:
        logger.error("OPENROUTER_API_KEY required")
        sys.exit(1)

    async with async_session() as db:
        result = await db.execute(select(Project).where(Project.embedding.is_(None)))
        projects = result.scalars().all()
        if not projects:
            logger.info("All projects already embedded.")
            return

        logger.info("Embedding %d projects...", len(projects))

        ok, fail = 0, 0
        async with httpx.AsyncClient(timeout=60.0) as client:
            for i, project in enumerate(projects, 1):
                tags = ", ".join(project.tags or [])
                stack = ", ".join(project.tech_stack or [])
                embed_text = f"{project.title}. {project.description}. Теги: {tags}. Стек: {stack}"

                try:
                    resp = await client.post(
                        "https://openrouter.ai/api/v1/embeddings",
                        headers={"Authorization": f"Bearer {api_key}"},
                        json={"model": settings.embedding_model, "input": embed_text},
                    )
                    if resp.status_code != 200:
                        logger.warning(
                            "[%d/%d] FAIL %s: HTTP %d %s",
                            i, len(projects), project.title, resp.status_code, resp.text[:100],
                        )
                        fail += 1
                        continue

                    embedding = resp.json()["data"][0]["embedding"]
                    emb_str = "[" + ",".join(str(x) for x in embedding) + "]"
                    await db.execute(
                        sql_text(
                            "UPDATE projects SET embedding = cast(:emb as vector) "
                            "WHERE id = cast(:pid as uuid)"
                        ),
                        {"emb": emb_str, "pid": str(project.id)},
                    )
                    ok += 1
                    if i % 10 == 0:
                        await db.commit()
                        logger.info("[%d/%d] committed (ok=%d fail=%d)", i, len(projects), ok, fail)
                except Exception as e:
                    logger.warning("[%d/%d] EXC %s: %s", i, len(projects), project.title, e)
                    fail += 1

        await db.commit()
        logger.info("Done. ok=%d fail=%d total=%d", ok, fail, len(projects))


if __name__ == "__main__":
    asyncio.run(main())
