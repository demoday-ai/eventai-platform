import asyncio
import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import delete, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.project import Project
from src.models.recommendation import Recommendation
from src.models.schedule_slot import ScheduleSlot
from src.models.room import Room
from src.services.platform_client import PlatformClient

logger = logging.getLogger(__name__)

from src.core.config import settings

_semaphore: asyncio.Semaphore | None = None


def _get_semaphore() -> asyncio.Semaphore:
    global _semaphore
    if _semaphore is None:
        _semaphore = asyncio.Semaphore(settings.semaphore_limit)
    return _semaphore


async def generate_recommendations(
    db: AsyncSession,
    platform: PlatformClient,
    profile_id: UUID,
    event_id: UUID,
    profile_text: str,
    selected_tags: list[str] | None = None,
) -> list[Recommendation]:
    """Full recommendation pipeline with semaphore and timeout."""
    try:
        sem = _get_semaphore()
        await asyncio.wait_for(sem.acquire(), timeout=10.0)
    except asyncio.TimeoutError:
        logger.warning("Semaphore timeout, falling back to tag overlap")
        return await _fallback_tag_overlap(db, profile_id, event_id, selected_tags or [])

    try:
        # Budget must exceed the LLM-rerank timeout (8s) plus embedding+queries,
        # so a slow rerank falls back to vector order INSIDE the pipeline rather
        # than tripping this outer timeout into the useless tag-overlap fallback.
        return await asyncio.wait_for(
            _generate_pipeline(db, platform, profile_id, event_id, profile_text, selected_tags),
            timeout=25.0,
        )
    except asyncio.TimeoutError:
        logger.warning("Pipeline timeout, falling back to tag overlap")
        return await _fallback_tag_overlap(db, profile_id, event_id, selected_tags or [])
    except Exception as e:
        logger.error("Pipeline failed: %s", e)
        return await _fallback_tag_overlap(db, profile_id, event_id, selected_tags or [])
    finally:
        sem.release()


async def _generate_pipeline(
    db: AsyncSession,
    platform: PlatformClient,
    profile_id: UUID,
    event_id: UUID,
    profile_text: str,
    selected_tags: list[str] | None,
) -> list[Recommendation]:
    # 1. Embed profile
    try:
        embedding = await platform.embedding(profile_text)
    except Exception as e:
        logger.error("Embedding failed: %s", e)
        return await _fallback_tag_overlap(db, profile_id, event_id, selected_tags or [])

    # 2. pgvector cosine search top-N. Take a wider net (25) because Gemini
    # similarities are compressed and the relevant set isn't cleanly separable
    # by cosine alone — the LLM reranker does the semantic separation next.
    candidates = await _pgvector_search(db, embedding, event_id, limit=25)

    if len(candidates) < 5:
        logger.info("Few pgvector results (%d), padding with popular projects", len(candidates))
        candidates = await _pad_results(db, candidates, event_id, min_count=10)

    # 2b. LLM re-rank by profile relevance (fixes compressed-cosine noise).
    # On failure returns vector order unchanged — no candidates lost.
    candidates = await _llm_rerank(platform, profile_text, candidates)

    # 3. Load schedule slots
    slots = await _load_schedule_slots(db, event_id)

    # 4. Filter past slots
    now = datetime.now(timezone.utc)
    candidates = _filter_past_slots(candidates, slots, now)

    # 5. Schedule-aware rerank
    ranked = _schedule_rerank(candidates, slots)

    # 6. Save recommendations and return Recommendation objects
    return await _save_recommendations(db, profile_id, ranked)


async def _pgvector_search(
    db: AsyncSession, embedding: list[float], event_id: UUID, limit: int = 30
) -> list[dict]:
    """Cosine similarity search using pgvector."""
    embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"

    result = await db.execute(
        text("""
            SELECT id, title, description,
                   tags_json AS tags, tech_stack_json AS tech_stack,
                   author, telegram_contact, parsed_content,
                   embedding <=> cast(:embedding as vector) AS distance
            FROM projects
            WHERE event_id = cast(:event_id as uuid) AND embedding IS NOT NULL
            ORDER BY embedding <=> cast(:embedding as vector)
            LIMIT :limit
        """),
        {"embedding": embedding_str, "event_id": str(event_id), "limit": limit},
    )

    rows = result.mappings().all()
    return [
        {
            "project_id": row["id"],
            "title": row["title"],
            "description": row["description"],
            "tags": row["tags"] or [],
            "tech_stack": row["tech_stack"] or [],
            "author": row["author"],
            "telegram_contact": row["telegram_contact"],
            "parsed_content": row["parsed_content"],
            "score": max(0, 1 - row["distance"]) * 100,  # cosine similarity -> 0-100
        }
        for row in rows
    ]


async def _llm_rerank(
    platform: PlatformClient,
    profile_text: str,
    candidates: list[dict],
    timeout: float = 8.0,
) -> list[dict]:
    """Re-rank vector candidates by profile relevance via LLM.

    Gemini embeddings have a compressed similarity range (~55-75%), so the raw
    cosine score can't separate relevant from off-topic. The LLM reads the
    profile + candidate titles/descriptions, reorders by true relevance and
    drops clearly off-topic items.

    Has its OWN timeout: a slow LLM falls back to vector order here instead of
    bubbling up to the pipeline timeout (which would trigger the useless
    tag-overlap fallback). On any failure the input order is returned unchanged.
    """
    if not candidates:
        return []

    import json

    lines = []
    for i, c in enumerate(candidates, 1):
        desc = (c.get("description") or "")[:200]
        lines.append(f"{i}. {c['title']}: {desc}")
    catalog = "\n".join(lines)

    system = (
        "Ты ранжируешь проекты Demo Day по релевантности интересам гостя.\n"
        "Верни СТРОГО JSON: {\"ranking\": [{\"index\": N, \"relevant\": true|false}, ...]}\n"
        "index - номер проекта из списка. Порядок в ranking = порядок по убыванию "
        "релевантности. relevant=false для проектов НЕ по теме запроса гостя "
        "(их покажем в 'если успеете'). Включи ВСЕ проекты из списка ровно один раз."
    )
    user = f"Интересы гостя: {profile_text}\n\nПроекты:\n{catalog}"

    try:
        resp = await asyncio.wait_for(
            platform.chat_completion(
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                response_format={"type": "json_object"},
            ),
            timeout=timeout,
        )
        content = resp["choices"][0]["message"]["content"]
        ranking = json.loads(content).get("ranking", [])
        if not ranking:
            return candidates

        by_index = {i + 1: c for i, c in enumerate(candidates)}
        seen: set[int] = set()
        relevant: list[dict] = []
        irrelevant: list[dict] = []
        for item in ranking:
            idx = item.get("index")
            cand = by_index.get(idx)
            if cand is None or idx in seen:
                continue
            seen.add(idx)
            if item.get("relevant", True):
                relevant.append(cand)
            else:
                irrelevant.append(cand)
        # Any candidate the LLM omitted: keep at the end in vector order.
        leftovers = [c for i, c in by_index.items() if i not in seen]
        ordered = relevant + irrelevant + leftovers

        # Re-score so downstream rerank/threshold reflects LLM order:
        # relevant get a high band (descending), the rest a low band.
        n_rel = len(relevant)
        for pos, c in enumerate(ordered):
            if pos < n_rel:
                c["score"] = 100.0 - pos  # 100, 99, ... relevant cluster
            else:
                c["score"] = 40.0 - pos   # clearly below the must-visit threshold
        return ordered
    except Exception as e:
        logger.warning("LLM rerank failed (%s), keeping vector order", e)
        return candidates


def _filter_past_slots(candidates: list[dict], slots: dict[UUID, dict], now: datetime) -> list[dict]:
    """Remove projects whose slot has already passed."""
    # Make now naive if slot times are naive (PostgreSQL TIMESTAMP without tz)
    now_naive = now.replace(tzinfo=None) if now.tzinfo else now
    filtered = []
    for c in candidates:
        slot = slots.get(c["project_id"])
        if slot and slot["start_time"].replace(tzinfo=None) < now_naive:
            continue
        filtered.append(c)
    return filtered


def _schedule_rerank(candidates: list[dict], slots: dict[UUID, dict]) -> list[dict]:
    """Greedy slot assignment with room bonus and conflict penalty."""
    assigned_slots: set[datetime] = set()  # start_time values already taken
    assigned_rooms: dict[UUID, int] = {}   # room_id -> count
    last_room_id: UUID | None = None

    ranked: list[dict] = []

    # Sort by score descending
    candidates.sort(key=lambda c: c["score"], reverse=True)

    for candidate in candidates:
        slot = slots.get(candidate["project_id"])

        if slot:
            # Slot conflict: skip if this time slot is taken
            if slot["start_time"] in assigned_slots:
                continue

            room_id = slot["room_id"]

            # Room bonus: +3.0 if same room as previous
            if last_room_id and room_id == last_room_id:
                candidate["score"] += 3.0

            assigned_slots.add(slot["start_time"])
            assigned_rooms[room_id] = assigned_rooms.get(room_id, 0) + 1
            last_room_id = room_id

            candidate["slot"] = slot

        ranked.append(candidate)

    # Assign categories: must_visit is position AND relevance driven.
    # A candidate far below the top score (cliff) must not be "обязательно
    # к посещению" just because it landed in top-8 — it goes to if_time.
    top_score = ranked[0]["score"] if ranked else 0.0
    threshold = top_score * 0.6
    must_count = 0
    for i, r in enumerate(ranked):
        r["rank"] = i + 1
        is_must = i < 8 and r["score"] >= threshold
        r["category"] = "must_visit" if is_must else "if_time"
        if is_must:
            must_count += 1
            r["visit_order"] = must_count
        else:
            r["visit_order"] = None

    return ranked[:15]


async def _fallback_tag_overlap(
    db: AsyncSession, profile_id: UUID, event_id: UUID, tags: list[str]
) -> list[Recommendation]:
    """Fallback: score projects by tag overlap (case-insensitive).

    If user has no tags or no project overlaps, score is 0 for everyone -- in that
    case we add a small random nudge so the order is not deterministically alphabetical
    (which made every guest receive the exact same A2AS, Adapstory, ... program).
    """
    import random

    result = await db.execute(
        select(Project).where(Project.event_id == event_id)
    )
    projects = result.scalars().all()

    lower_tags = {t.lower() for t in tags}

    scored: list[dict] = []
    for p in projects:
        project_tags = {t.lower() for t in (p.tags or [])}
        overlap = len(lower_tags & project_tags)
        # base: 20 points per matched tag; random tiebreaker 0..10 so we never end up
        # alphabetical when many projects share the same overlap (or when overlap=0).
        score = overlap * 20.0 + random.uniform(0, 10)
        scored.append({"project_id": p.id, "title": p.title, "score": score, "rank": 0, "category": "must_visit"})

    scored.sort(key=lambda x: x["score"], reverse=True)

    recs: list[Recommendation] = []
    for i, s in enumerate(scored[:15]):
        s["rank"] = i + 1
        s["category"] = "must_visit" if i < 8 else "if_time"
        rec = Recommendation(
            guest_profile_id=profile_id,
            project_id=s["project_id"],
            relevance_score=s["score"],
            category=s["category"],
            rank=s["rank"],
        )
        recs.append(rec)

    # Delete old + save new
    await db.execute(delete(Recommendation).where(Recommendation.guest_profile_id == profile_id))
    db.add_all(recs)
    await db.flush()

    return recs


async def _pad_results(
    db: AsyncSession, candidates: list[dict], event_id: UUID, min_count: int = 10
) -> list[dict]:
    """Pad with popular projects if too few results."""
    if len(candidates) >= min_count:
        return candidates

    existing_ids = {c["project_id"] for c in candidates}

    # Order by random() so different guests don't always get the same alphabetical
    # tail (was causing every program to look identical when pgvector returned 0).
    result = await db.execute(
        select(Project)
        .where(Project.event_id == event_id)
        .where(Project.id.notin_(existing_ids))
        .order_by(func.random())
        .limit(min_count - len(candidates))
    )

    import random

    for p in result.scalars().all():
        candidates.append({
            "project_id": p.id,
            "title": p.title,
            "description": p.description,
            "tags": p.tags or [],
            "tech_stack": p.tech_stack or [],
            "author": p.author,
            "telegram_contact": p.telegram_contact,
            "parsed_content": p.parsed_content,
            # spread scores 5-15 so downstream rerank doesn't tie-break alphabetically
            "score": 5.0 + random.uniform(0, 10),
        })

    return candidates


async def _load_schedule_slots(db: AsyncSession, event_id: UUID) -> dict[UUID, dict]:
    """Load schedule slots keyed by project_id."""
    result = await db.execute(
        select(ScheduleSlot, Room.name.label("room_name"), Room.display_order)
        .join(Room, ScheduleSlot.room_id == Room.id)
        .where(ScheduleSlot.event_id == event_id)
    )

    slots: dict[UUID, dict] = {}
    for row in result.all():
        slot = row[0]
        slots[slot.project_id] = {
            "slot_id": slot.id,
            "room_id": slot.room_id,
            "room_name": row.room_name,
            "start_time": slot.start_time,
            "end_time": slot.end_time,
            "day_number": slot.display_order,
        }

    return slots


async def _save_recommendations(
    db: AsyncSession, profile_id: UUID, ranked: list[dict]
) -> list[Recommendation]:
    """Delete old recommendations and save new ones."""
    await db.execute(delete(Recommendation).where(Recommendation.guest_profile_id == profile_id))

    recs = []
    for r in ranked:
        slot = r.get("slot")
        rec = Recommendation(
            guest_profile_id=profile_id,
            project_id=r["project_id"],
            relevance_score=r["score"],
            category=r["category"],
            rank=r["rank"],
            slot_id=slot["slot_id"] if slot else None,
            visit_order=r.get("visit_order"),
        )
        db.add(rec)
        recs.append(rec)

    await db.flush()
    return recs
