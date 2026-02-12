"""Tests for project tag generation: heuristic matching, LLM extraction, generate_missing_tags."""

import asyncio
from datetime import date
from unittest.mock import AsyncMock, patch

import pytest

from app.models.event import Event
from app.models.project import Project
from app.models.tag import Tag
from app.services.admin.project_service import (
    _extract_tags_via_llm,
    _match_tags_heuristic,
    generate_missing_tags,
)

# ---------------------------------------------------------------------------
# Heuristic matching tests
# ---------------------------------------------------------------------------


def test_match_tags_heuristic_short_tags():
    """Short tags (CV, NLP, ML) should match via word boundary regex."""
    text = "Проект по NLP и CV для обработки данных"
    tags = ["NLP", "CV", "ML", "EdTech"]
    result = _match_tags_heuristic(text, tags)
    assert "NLP" in result
    assert "CV" in result
    assert "ML" not in result


def test_match_tags_heuristic_long_tags():
    """Long tags (EdTech, FinTech) should match via substring."""
    text = "Платформа EdTech для обучения FinTech специалистов"
    tags = ["NLP", "EdTech", "FinTech", "MedTech"]
    result = _match_tags_heuristic(text, tags)
    assert "EdTech" in result
    assert "FinTech" in result
    assert "MedTech" not in result


def test_match_tags_heuristic_no_false_positives():
    """'Novelty' should NOT match 'NLP'; unrelated text should not match short tags."""
    text = "Novelty detection and anomaly scoring"
    tags = ["NLP", "CV", "ML"]
    result = _match_tags_heuristic(text, tags)
    assert "NLP" not in result


def test_match_tags_heuristic_case_insensitive():
    """Both 'nlp' and 'NLP' in text should match the NLP tag."""
    tags = ["NLP", "CV"]
    assert "NLP" in _match_tags_heuristic("проект nlp", tags)
    assert "NLP" in _match_tags_heuristic("проект NLP", tags)


# ---------------------------------------------------------------------------
# LLM extraction tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_extract_tags_via_llm_success():
    """LLM returns valid tags — they should be returned as-is."""
    available = ["NLP", "CV", "EdTech", "Other"]
    mock_response = {"tags": ["NLP", "EdTech"]}

    with patch(
        "app.services.core.llm_client.send_chat_completion",
        new_callable=AsyncMock,
        return_value=mock_response,
    ):
        result = await _extract_tags_via_llm("AI education platform", available)

    assert result == ["NLP", "EdTech"]


@pytest.mark.asyncio
async def test_extract_tags_via_llm_filters_invalid():
    """LLM returns a tag not in available_tags — it should be filtered out."""
    available = ["NLP", "CV", "Other"]
    mock_response = {"tags": ["NLP", "FakeTag"]}

    with patch(
        "app.services.core.llm_client.send_chat_completion",
        new_callable=AsyncMock,
        return_value=mock_response,
    ):
        result = await _extract_tags_via_llm("text about NLP", available)

    assert result == ["NLP"]
    assert "FakeTag" not in result


@pytest.mark.asyncio
async def test_extract_tags_via_llm_graceful_failure():
    """LLM raises exception — should return empty list, not crash."""
    with patch(
        "app.services.core.llm_client.send_chat_completion",
        new_callable=AsyncMock,
        side_effect=RuntimeError("API down"),
    ):
        result = await _extract_tags_via_llm("some text", ["NLP", "CV"])

    assert result == []


# ---------------------------------------------------------------------------
# Integration: generate_missing_tags
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_missing_tags_heuristic_only(session):
    """Project with 'NLP' in title should get tagged by heuristic, no LLM call."""
    event = Event(name="Test DD", start_date=date.today(), end_date=date.today())
    session.add(event)
    await session.flush()

    tag = Tag(name="NLP")
    session.add(tag)
    await session.flush()

    project = Project(
        event_id=event.id,
        title="NLP Chatbot",
        description="A chatbot using NLP techniques",
        author="Test",
        telegram_contact="@test",
        source="upload",
    )
    session.add(project)
    await session.flush()

    with patch("app.services.admin.project_service._extract_tags_via_llm") as mock_llm:
        result = await generate_missing_tags(session, event.id)
        mock_llm.assert_not_called()

    assert result["processed"] == 1
    assert result["tagged"] == 1


@pytest.mark.asyncio
async def test_generate_missing_tags_llm_fallback(session):
    """Project without keyword matches should fall back to LLM."""
    event = Event(name="Test DD2", start_date=date.today(), end_date=date.today())
    session.add(event)
    await session.flush()

    tag_edtech = Tag(name="EdTech")
    tag_other2 = Tag(name="Recsys")
    session.add_all([tag_edtech, tag_other2])
    await session.flush()

    project = Project(
        event_id=event.id,
        title="Smart Assistant",
        description="An intelligent helper for daily tasks",
        author="Test",
        telegram_contact="@test",
        source="upload",
    )
    session.add(project)
    await session.flush()

    with patch(
        "app.services.admin.project_service._extract_tags_via_llm",
        new_callable=AsyncMock,
        return_value=["EdTech"],
    ) as mock_llm:
        result = await generate_missing_tags(session, event.id)
        mock_llm.assert_called_once()

    assert result["processed"] == 1
    assert result["tagged"] == 1


@pytest.mark.asyncio
async def test_generate_missing_tags_other_fallback(session):
    """When LLM returns empty, project should get 'Other' tag."""
    event = Event(name="Test DD3", start_date=date.today(), end_date=date.today())
    session.add(event)
    await session.flush()

    tag_other = Tag(name="Other")
    session.add(tag_other)
    await session.flush()

    project = Project(
        event_id=event.id,
        title="Mystery Box",
        description="Something completely different",
        author="Test",
        telegram_contact="@test",
        source="upload",
    )
    session.add(project)
    await session.flush()

    with patch(
        "app.services.admin.project_service._extract_tags_via_llm",
        new_callable=AsyncMock,
        return_value=[],
    ):
        result = await generate_missing_tags(session, event.id)

    assert result["processed"] == 1
    assert result["tagged"] == 1


@pytest.mark.asyncio
async def test_generate_missing_tags_cancellation(session):
    """CancelledError from progress_callback should stop tag generation."""
    event = Event(name="Test DD Cancel", start_date=date.today(), end_date=date.today())
    session.add(event)
    await session.flush()

    tag_sec = Tag(name="Security")
    session.add(tag_sec)
    await session.flush()

    project = Project(
        event_id=event.id,
        title="Threat Detector",
        description="Just a generic project for cancellation test",
        author="Test",
        telegram_contact="@test",
        source="upload",
    )
    session.add(project)
    await session.flush()

    call_count = 0

    def cancelling_callback(progress: dict):
        nonlocal call_count
        call_count += 1
        # Cancel on the second callback (after heuristic phase)
        if call_count >= 2:
            raise asyncio.CancelledError("User cancelled")

    with patch(
        "app.services.admin.project_service._extract_tags_via_llm",
        new_callable=AsyncMock,
        return_value=["Security"],
    ):
        with pytest.raises(asyncio.CancelledError):
            await generate_missing_tags(session, event.id, progress_callback=cancelling_callback)
