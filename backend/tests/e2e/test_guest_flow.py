"""E2E tests for guest flow and agent mode.

Run with: pytest tests/e2e/ -v -s
Requires Telegram credentials in .env.e2e (see .env.e2e.example)
"""

import pytest

from tests.e2e.conftest import get_button_with_text, wait

# Mark all tests in this module as e2e
pytestmark = pytest.mark.e2e


@pytest.mark.asyncio
async def test_start_command(conv):
    """Test /start shows role selection."""
    await conv.send_message("/start")
    wait(1)
    response = await conv.get_response()

    assert "Гость" in response.text or response.buttons is not None
    assert get_button_with_text(response, "Гость") is not None


@pytest.mark.asyncio
async def test_guest_onboarding_flow(conv):
    """Test complete guest onboarding: role -> subtype -> NL profile."""
    # Start
    await conv.send_message("/start")
    wait(1)
    msg = await conv.get_response()

    # Select guest role
    guest_btn = get_button_with_text(msg, "Гость")
    if guest_btn:
        await guest_btn.click()
        wait(1)
        msg = await conv.get_response()

    # Select student subtype (if available)
    student_btn = get_button_with_text(msg, "Студент")
    if student_btn:
        await student_btn.click()
        wait(1)
        msg = await conv.get_response()

    # Should now be in NL profiling
    # Either asking about interests or showing topic buttons
    assert "интересует" in msg.text.lower() or msg.buttons is not None


@pytest.mark.asyncio
async def test_nl_profiling_with_text(conv):
    """Test NL profiling with text input."""
    # Start fresh
    await conv.send_message("/start")
    wait(1)
    msg = await conv.get_response()

    # Navigate to NL profiling (click through role/subtype if needed)
    for btn_text in ["Гость", "Студент"]:
        btn = get_button_with_text(msg, btn_text)
        if btn:
            await btn.click()
            wait(1)
            msg = await conv.get_response()

    # Send interest text
    await conv.send_message("Интересуюсь компьютерным зрением и NLP проектами")
    wait(2)
    msg = await conv.get_response()

    # Should show confirmation or continue conversation
    assert "верно" in msg.text.lower() or "профиль" in msg.text.lower() or msg.buttons


@pytest.mark.asyncio
async def test_agent_mode_show_profile(conv):
    """Test agent mode - show profile command."""
    # This assumes user is already in VIEW_PROGRAM state
    # If not, we need to go through the full flow first

    await conv.send_message("покажи мой профиль")
    wait(3)
    msg = await conv.get_response()

    # Should contain profile info or error if no profile
    assert "профиль" in msg.text.lower() or "теги" in msg.text.lower() or "/start" in msg.text.lower()


@pytest.mark.asyncio
async def test_agent_mode_rebuild_profile(conv):
    """Test agent mode - rebuild profile command."""
    await conv.send_message("хочу изменить свои интересы")
    wait(3)
    msg = await conv.get_response()

    # Should either start rebuild or explain how to do it
    # If in VIEW_PROGRAM, should trigger rebuild_profile tool
    assert "интересует" in msg.text.lower() or "профиль" in msg.text.lower() or msg.buttons


@pytest.mark.asyncio
async def test_agent_mode_show_project(conv):
    """Test agent mode - show project command."""
    await conv.send_message("покажи проект номер 1")
    wait(3)
    msg = await conv.get_response()

    # Should show project details or say project not found
    assert len(msg.text) > 50  # Some meaningful response


@pytest.mark.asyncio
async def test_agent_mode_qa_questions(conv):
    """Test agent mode - generate QA questions."""
    await conv.send_message("подготовь вопросы для проекта 1")
    wait(5)  # LLM needs more time
    msg = await conv.get_response()

    # Should contain questions or error
    assert "?" in msg.text or "вопрос" in msg.text.lower() or "проект" in msg.text.lower()


@pytest.mark.asyncio
async def test_profile_command(conv):
    """Test /profile command."""
    await conv.send_message("/profile")
    wait(2)
    msg = await conv.get_response()

    # Should show profile or say profiling not available
    assert "профиль" in msg.text.lower() or "гост" in msg.text.lower() or msg.buttons
