"""
Unit tests for retriever service functions.
Tests the pure/helper functions from src/services/retriever.py.
Supplements test_e2e.py with focused unit tests.
"""

import asyncio
import os
import pytest
from datetime import datetime, timedelta, timezone
from uuid import uuid4

os.environ.setdefault("BOT_TOKEN", "test")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://eventai:eventai@localhost:5432/eventai")
os.environ.setdefault("REDIS_URL", "redis://:testpassword@localhost:6379/0")

from src.services.retriever import (
    _filter_past_slots,
    _schedule_rerank,
    _get_semaphore,
)


# ---------------------------------------------------------------------------
# _filter_past_slots tests
# ---------------------------------------------------------------------------


class TestFilterPastSlots:

    def test_filter_past_slots(self):
        """Filters out projects with past start_time."""
        now = datetime(2026, 5, 15, 12, 0, tzinfo=timezone.utc)
        past_time = datetime(2026, 5, 15, 10, 0, tzinfo=timezone.utc)

        p1 = uuid4()
        p2 = uuid4()

        candidates = [
            {"project_id": p1, "title": "Past", "score": 90.0},
            {"project_id": p2, "title": "NoSlot", "score": 80.0},
        ]

        slots = {
            p1: {
                "slot_id": uuid4(),
                "room_id": uuid4(),
                "room_name": "Room A",
                "start_time": past_time,
                "end_time": past_time + timedelta(minutes=20),
                "day_number": 1,
            },
        }

        filtered = _filter_past_slots(candidates, slots, now)

        assert len(filtered) == 1
        assert filtered[0]["title"] == "NoSlot"

    def test_filter_past_slots_keeps_future(self):
        """Keeps projects with future start_time."""
        now = datetime(2026, 5, 15, 10, 0, tzinfo=timezone.utc)
        future_time = datetime(2026, 5, 15, 14, 0, tzinfo=timezone.utc)

        p1 = uuid4()

        candidates = [
            {"project_id": p1, "title": "Future", "score": 85.0},
        ]

        slots = {
            p1: {
                "slot_id": uuid4(),
                "room_id": uuid4(),
                "room_name": "Room A",
                "start_time": future_time,
                "end_time": future_time + timedelta(minutes=20),
                "day_number": 1,
            },
        }

        filtered = _filter_past_slots(candidates, slots, now)

        assert len(filtered) == 1
        assert filtered[0]["title"] == "Future"

    def test_filter_past_slots_no_slot(self):
        """Projects without slot are kept."""
        now = datetime(2026, 5, 15, 12, 0, tzinfo=timezone.utc)
        p1 = uuid4()

        candidates = [
            {"project_id": p1, "title": "NoSlot", "score": 70.0},
        ]

        slots = {}

        filtered = _filter_past_slots(candidates, slots, now)

        assert len(filtered) == 1
        assert filtered[0]["title"] == "NoSlot"

    def test_filter_past_slots_all_past(self):
        """All slots past -> empty result."""
        now = datetime(2026, 5, 15, 18, 0, tzinfo=timezone.utc)
        past1 = datetime(2026, 5, 15, 10, 0, tzinfo=timezone.utc)
        past2 = datetime(2026, 5, 15, 11, 0, tzinfo=timezone.utc)

        p1, p2 = uuid4(), uuid4()

        candidates = [
            {"project_id": p1, "title": "P1", "score": 90.0},
            {"project_id": p2, "title": "P2", "score": 80.0},
        ]

        slots = {
            p1: {"slot_id": uuid4(), "room_id": uuid4(), "room_name": "A", "start_time": past1, "end_time": past1 + timedelta(minutes=20), "day_number": 1},
            p2: {"slot_id": uuid4(), "room_id": uuid4(), "room_name": "B", "start_time": past2, "end_time": past2 + timedelta(minutes=20), "day_number": 1},
        }

        filtered = _filter_past_slots(candidates, slots, now)

        assert len(filtered) == 0

    def test_filter_past_slots_mixed(self):
        """Mix of past, future, and no-slot projects."""
        now = datetime(2026, 5, 15, 12, 0, tzinfo=timezone.utc)
        past_time = datetime(2026, 5, 15, 9, 0, tzinfo=timezone.utc)
        future_time = datetime(2026, 5, 15, 15, 0, tzinfo=timezone.utc)

        p1, p2, p3 = uuid4(), uuid4(), uuid4()

        candidates = [
            {"project_id": p1, "title": "Past", "score": 95.0},
            {"project_id": p2, "title": "Future", "score": 85.0},
            {"project_id": p3, "title": "NoSlot", "score": 75.0},
        ]

        slots = {
            p1: {"slot_id": uuid4(), "room_id": uuid4(), "room_name": "A", "start_time": past_time, "end_time": past_time + timedelta(minutes=20), "day_number": 1},
            p2: {"slot_id": uuid4(), "room_id": uuid4(), "room_name": "B", "start_time": future_time, "end_time": future_time + timedelta(minutes=20), "day_number": 1},
        }

        filtered = _filter_past_slots(candidates, slots, now)

        assert len(filtered) == 2
        titles = {c["title"] for c in filtered}
        assert "Past" not in titles
        assert "Future" in titles
        assert "NoSlot" in titles


# ---------------------------------------------------------------------------
# _schedule_rerank tests
# ---------------------------------------------------------------------------


class TestScheduleRerank:

    def test_schedule_rerank_room_bonus(self):
        """Project in same room as previous gets +3.0 bonus."""
        room_a = uuid4()
        t1 = datetime(2026, 5, 15, 10, 0, tzinfo=timezone.utc)
        t2 = datetime(2026, 5, 15, 10, 20, tzinfo=timezone.utc)

        p1, p2 = uuid4(), uuid4()

        candidates = [
            {"project_id": p1, "title": "P1", "score": 90.0},
            {"project_id": p2, "title": "P2", "score": 85.0},
        ]

        slots = {
            p1: {"slot_id": uuid4(), "room_id": room_a, "room_name": "Room A", "start_time": t1, "end_time": t1 + timedelta(minutes=20), "day_number": 1},
            p2: {"slot_id": uuid4(), "room_id": room_a, "room_name": "Room A", "start_time": t2, "end_time": t2 + timedelta(minutes=20), "day_number": 1},
        }

        ranked = _schedule_rerank(candidates, slots)

        assert ranked[0]["title"] == "P1"
        assert ranked[0]["score"] == 90.0  # no bonus for first
        assert ranked[1]["title"] == "P2"
        assert ranked[1]["score"] == 88.0  # 85 + 3.0 room bonus

    def test_schedule_rerank_conflict_exclusion(self):
        """Two projects at same time, second (lower score) excluded."""
        room_a = uuid4()
        room_b = uuid4()
        t1 = datetime(2026, 5, 15, 10, 0, tzinfo=timezone.utc)

        p1, p2 = uuid4(), uuid4()

        candidates = [
            {"project_id": p1, "title": "P1", "score": 90.0},
            {"project_id": p2, "title": "P2", "score": 80.0},
        ]

        slots = {
            p1: {"slot_id": uuid4(), "room_id": room_a, "room_name": "Room A", "start_time": t1, "end_time": t1 + timedelta(minutes=20), "day_number": 1},
            p2: {"slot_id": uuid4(), "room_id": room_b, "room_name": "Room B", "start_time": t1, "end_time": t1 + timedelta(minutes=20), "day_number": 1},
        }

        ranked = _schedule_rerank(candidates, slots)

        # Only P1 should be included - P2 conflicts on same start_time
        assert len(ranked) == 1
        assert ranked[0]["title"] == "P1"

    def test_schedule_rerank_categories(self):
        """First 8 = must_visit, rest = if_time."""
        room = uuid4()
        base_time = datetime(2026, 5, 15, 10, 0, tzinfo=timezone.utc)

        candidates = []
        slots = {}

        for i in range(12):
            pid = uuid4()
            t = base_time + timedelta(minutes=20 * i)
            candidates.append({"project_id": pid, "title": f"P{i+1}", "score": 100.0 - i})
            slots[pid] = {
                "slot_id": uuid4(),
                "room_id": room,
                "room_name": "Room A",
                "start_time": t,
                "end_time": t + timedelta(minutes=20),
                "day_number": 1,
            }

        ranked = _schedule_rerank(candidates, slots)

        # First 8 should be must_visit
        for i in range(min(8, len(ranked))):
            assert ranked[i]["category"] == "must_visit"
            assert ranked[i]["visit_order"] == i + 1

        # 9+ should be if_time
        for i in range(8, len(ranked)):
            assert ranked[i]["category"] == "if_time"
            assert ranked[i]["visit_order"] is None

    def test_schedule_rerank_truncates_to_15(self):
        """Output is capped at 15 results."""
        room = uuid4()
        base_time = datetime(2026, 5, 15, 10, 0, tzinfo=timezone.utc)

        candidates = []
        slots = {}

        for i in range(20):
            pid = uuid4()
            t = base_time + timedelta(minutes=20 * i)
            candidates.append({"project_id": pid, "title": f"P{i+1}", "score": 100.0 - i})
            slots[pid] = {
                "slot_id": uuid4(),
                "room_id": room,
                "room_name": "Room A",
                "start_time": t,
                "end_time": t + timedelta(minutes=20),
                "day_number": 1,
            }

        ranked = _schedule_rerank(candidates, slots)

        assert len(ranked) <= 15

    def test_schedule_rerank_no_slots(self):
        """Projects without slots are included, no conflicts."""
        p1, p2 = uuid4(), uuid4()

        candidates = [
            {"project_id": p1, "title": "P1", "score": 90.0},
            {"project_id": p2, "title": "P2", "score": 80.0},
        ]

        slots = {}  # no schedule data

        ranked = _schedule_rerank(candidates, slots)

        assert len(ranked) == 2
        assert ranked[0]["title"] == "P1"
        assert ranked[1]["title"] == "P2"

    def test_schedule_rerank_preserves_score_order(self):
        """Higher score projects come first."""
        room = uuid4()
        t1 = datetime(2026, 5, 15, 10, 0, tzinfo=timezone.utc)
        t2 = datetime(2026, 5, 15, 10, 20, tzinfo=timezone.utc)

        p1, p2 = uuid4(), uuid4()

        # Note: input order doesn't matter, sort is by score
        candidates = [
            {"project_id": p2, "title": "Low", "score": 60.0},
            {"project_id": p1, "title": "High", "score": 95.0},
        ]

        slots = {
            p1: {"slot_id": uuid4(), "room_id": room, "room_name": "A", "start_time": t1, "end_time": t1 + timedelta(minutes=20), "day_number": 1},
            p2: {"slot_id": uuid4(), "room_id": room, "room_name": "A", "start_time": t2, "end_time": t2 + timedelta(minutes=20), "day_number": 1},
        }

        ranked = _schedule_rerank(candidates, slots)

        assert ranked[0]["title"] == "High"
        assert ranked[1]["title"] == "Low"

    def test_schedule_rerank_rank_assignment(self):
        """Each result gets sequential rank starting from 1."""
        p1, p2, p3 = uuid4(), uuid4(), uuid4()

        candidates = [
            {"project_id": p1, "title": "P1", "score": 90.0},
            {"project_id": p2, "title": "P2", "score": 80.0},
            {"project_id": p3, "title": "P3", "score": 70.0},
        ]

        ranked = _schedule_rerank(candidates, {})

        for i, r in enumerate(ranked):
            assert r["rank"] == i + 1

    def test_schedule_rerank_different_rooms_no_bonus(self):
        """Different rooms - no +3.0 bonus applied."""
        room_a = uuid4()
        room_b = uuid4()
        t1 = datetime(2026, 5, 15, 10, 0, tzinfo=timezone.utc)
        t2 = datetime(2026, 5, 15, 10, 20, tzinfo=timezone.utc)

        p1, p2 = uuid4(), uuid4()

        candidates = [
            {"project_id": p1, "title": "P1", "score": 90.0},
            {"project_id": p2, "title": "P2", "score": 85.0},
        ]

        slots = {
            p1: {"slot_id": uuid4(), "room_id": room_a, "room_name": "Room A", "start_time": t1, "end_time": t1 + timedelta(minutes=20), "day_number": 1},
            p2: {"slot_id": uuid4(), "room_id": room_b, "room_name": "Room B", "start_time": t2, "end_time": t2 + timedelta(minutes=20), "day_number": 1},
        }

        ranked = _schedule_rerank(candidates, slots)

        assert ranked[1]["score"] == 85.0  # no bonus


# ---------------------------------------------------------------------------
# _get_semaphore tests
# ---------------------------------------------------------------------------


class TestGetSemaphore:

    def test_get_semaphore_lazy_init(self):
        """Semaphore created on first call, reused on subsequent calls."""
        import src.services.retriever as retriever_mod

        # Reset global state
        original = retriever_mod._semaphore
        retriever_mod._semaphore = None

        try:
            sem1 = _get_semaphore()
            assert isinstance(sem1, asyncio.Semaphore)

            sem2 = _get_semaphore()
            assert sem1 is sem2  # same instance
        finally:
            retriever_mod._semaphore = original

    def test_get_semaphore_uses_settings_limit(self):
        """Semaphore uses settings.semaphore_limit value."""
        import src.services.retriever as retriever_mod
        from src.core.config import settings

        original = retriever_mod._semaphore
        retriever_mod._semaphore = None

        try:
            sem = _get_semaphore()
            # asyncio.Semaphore stores the initial value as _value
            assert sem._value == settings.semaphore_limit
        finally:
            retriever_mod._semaphore = original


class TestRelevanceThreshold:
    """must_visit must be driven by relevance, not by position alone:
    a candidate far below the top score lands in if_time even inside top-8."""

    def test_low_score_candidates_demoted_to_if_time(self):
        room = uuid4()
        base_time = datetime(2026, 5, 15, 10, 0, tzinfo=timezone.utc)

        candidates = []
        slots = {}
        # 3 strong (90+), 5 weak (<40) — weak ones must NOT be must_visit
        scores = [95.0, 92.0, 90.0, 38.0, 35.0, 33.0, 30.0, 28.0]
        for i, sc in enumerate(scores):
            pid = uuid4()
            t = base_time + timedelta(minutes=20 * i)
            candidates.append({"project_id": pid, "title": f"P{i+1}", "score": sc})
            slots[pid] = {
                "slot_id": uuid4(), "room_id": room, "room_name": "A",
                "start_time": t, "end_time": t + timedelta(minutes=20),
                "day_number": 1,
            }

        ranked = _schedule_rerank(candidates, slots)
        strong = [r for r in ranked if r["score"] >= 60]
        weak = [r for r in ranked if r["score"] < 60]
        assert all(r["category"] == "must_visit" for r in strong)
        assert all(r["category"] == "if_time" for r in weak)

    def test_uniform_high_scores_keep_top8_must_visit(self):
        """When everything is comparable, behave as before: top-8 must_visit."""
        room = uuid4()
        base_time = datetime(2026, 5, 15, 10, 0, tzinfo=timezone.utc)

        candidates = []
        slots = {}
        for i in range(12):
            pid = uuid4()
            t = base_time + timedelta(minutes=20 * i)
            candidates.append({"project_id": pid, "title": f"P{i+1}", "score": 90.0 - i})
            slots[pid] = {
                "slot_id": uuid4(), "room_id": room, "room_name": "A",
                "start_time": t, "end_time": t + timedelta(minutes=20),
                "day_number": 1,
            }

        ranked = _schedule_rerank(candidates, slots)
        assert sum(1 for r in ranked if r["category"] == "must_visit") == 8


class TestLLMRerank:
    """LLM re-ranking: vector gives top-N, LLM reorders by profile relevance
    and drops off-topic candidates (Gemini sims are compressed, so absolute
    vector score cannot separate relevant from noise)."""

    @pytest.mark.asyncio
    async def test_rerank_reorders_and_filters(self):
        import json
        from unittest.mock import AsyncMock, MagicMock
        from src.services.retriever import _llm_rerank

        c1 = {"project_id": uuid4(), "title": "Скоринг МТС", "description": "кредитный скоринг", "score": 74.0}
        c2 = {"project_id": uuid4(), "title": "Deepfake detection", "description": "детекция дипфейков", "score": 67.0}
        c3 = {"project_id": uuid4(), "title": "Антифрод банк", "description": "обнаружение мошенничества", "score": 66.0}

        platform = MagicMock()
        # LLM keeps the 2 fintech, drops deepfake, in this order: c3, c1
        platform.chat_completion = AsyncMock(return_value={
            "choices": [{"message": {"content": json.dumps({
                "ranking": [
                    {"index": 3, "relevant": True},
                    {"index": 1, "relevant": True},
                    {"index": 2, "relevant": False},
                ]
            })}}]
        })

        out = await _llm_rerank(platform, "финтех скоринг антифрод", [c1, c2, c3])
        titles = [c["title"] for c in out]
        # Relevant first in LLM order; off-topic sinks to the end (→ «если успеете»),
        # nothing lost. Deepfake last with a low score, not in the lead.
        assert titles[:2] == ["Антифрод банк", "Скоринг МТС"]
        assert titles[-1] == "Deepfake detection"
        assert out[1]["score"] >= 60 and out[-1]["score"] < 60

    @pytest.mark.asyncio
    async def test_rerank_falls_back_to_input_on_llm_error(self):
        from unittest.mock import AsyncMock, MagicMock
        from src.services.retriever import _llm_rerank

        cands = [
            {"project_id": uuid4(), "title": "A", "description": "x", "score": 70.0},
            {"project_id": uuid4(), "title": "B", "description": "y", "score": 60.0},
        ]
        platform = MagicMock()
        platform.chat_completion = AsyncMock(side_effect=Exception("LLM down"))

        out = await _llm_rerank(platform, "запрос", cands)
        # On failure: return input unchanged (vector order preserved, nothing lost)
        assert [c["title"] for c in out] == ["A", "B"]

    @pytest.mark.asyncio
    async def test_rerank_empty_candidates(self):
        from unittest.mock import AsyncMock, MagicMock
        from src.services.retriever import _llm_rerank

        platform = MagicMock()
        platform.chat_completion = AsyncMock()
        out = await _llm_rerank(platform, "q", [])
        assert out == []
        platform.chat_completion.assert_not_called()


class TestLLMRerankTimeout:
    """LLM rerank must fall back to vector order on its OWN timeout, so a slow
    LLM never bubbles up to the pipeline timeout -> useless tag-overlap fallback."""

    @pytest.mark.asyncio
    async def test_rerank_timeout_returns_vector_order(self):
        import asyncio
        from unittest.mock import AsyncMock, MagicMock
        from src.services.retriever import _llm_rerank

        cands = [
            {"project_id": uuid4(), "title": "A", "description": "x", "score": 70.0},
            {"project_id": uuid4(), "title": "B", "description": "y", "score": 60.0},
        ]

        async def slow(*a, **k):
            await asyncio.sleep(5)
            return {}

        platform = MagicMock()
        platform.chat_completion = slow

        out = await _llm_rerank(platform, "q", cands, timeout=0.2)
        assert [c["title"] for c in out] == ["A", "B"]
