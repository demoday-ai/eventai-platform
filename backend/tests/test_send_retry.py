"""Tests for send_retry service."""

from unittest.mock import AsyncMock, patch

import pytest

from app.services.core.send_retry import send_with_retry


@pytest.mark.asyncio
async def test_send_with_retry_success_first_attempt():
    bot = AsyncMock()
    bot.send_message = AsyncMock()

    success, error = await send_with_retry(bot, 123, "hello")

    assert success is True
    assert error is None
    bot.send_message.assert_awaited_once_with(
        chat_id=123,
        text="hello",
        parse_mode=None,
        disable_web_page_preview=False,
    )


@pytest.mark.asyncio
async def test_send_with_retry_passes_parse_mode():
    bot = AsyncMock()
    bot.send_message = AsyncMock()

    await send_with_retry(bot, 456, "msg", parse_mode="HTML", disable_web_page_preview=True)

    bot.send_message.assert_awaited_once_with(
        chat_id=456,
        text="msg",
        parse_mode="HTML",
        disable_web_page_preview=True,
    )


@pytest.mark.asyncio
async def test_send_with_retry_retries_on_failure():
    bot = AsyncMock()
    bot.send_message = AsyncMock(side_effect=[Exception("Network error"), None])

    with patch("app.services.core.send_retry.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        success, error = await send_with_retry(bot, 123, "hello", max_retries=3)

    assert success is True
    assert error is None
    assert bot.send_message.await_count == 2
    mock_sleep.assert_awaited_once_with(1)  # 2^0 = 1


@pytest.mark.asyncio
async def test_send_with_retry_fails_after_max_retries():
    bot = AsyncMock()
    bot.send_message = AsyncMock(side_effect=Exception("Blocked by user"))

    with patch("app.services.core.send_retry.asyncio.sleep", new_callable=AsyncMock):
        success, error = await send_with_retry(bot, 123, "hello", max_retries=3)

    assert success is False
    assert error == "Blocked by user"
    assert bot.send_message.await_count == 3


@pytest.mark.asyncio
async def test_send_with_retry_exponential_backoff():
    bot = AsyncMock()
    bot.send_message = AsyncMock(side_effect=[Exception("e1"), Exception("e2"), None])

    with patch("app.services.core.send_retry.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        success, error = await send_with_retry(bot, 123, "hello", max_retries=3)

    assert success is True
    assert mock_sleep.await_count == 2
    mock_sleep.assert_any_await(1)  # 2^0
    mock_sleep.assert_any_await(2)  # 2^1


@pytest.mark.asyncio
async def test_send_with_retry_truncates_long_error():
    bot = AsyncMock()
    long_error = "x" * 1000
    bot.send_message = AsyncMock(side_effect=Exception(long_error))

    with patch("app.services.core.send_retry.asyncio.sleep", new_callable=AsyncMock):
        success, error = await send_with_retry(bot, 123, "hello", max_retries=1)

    assert success is False
    assert len(error) == 500


@pytest.mark.asyncio
async def test_send_with_retry_single_attempt():
    bot = AsyncMock()
    bot.send_message = AsyncMock(side_effect=Exception("fail"))

    with patch("app.services.core.send_retry.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        success, error = await send_with_retry(bot, 123, "hello", max_retries=1)

    assert success is False
    assert error == "fail"
    mock_sleep.assert_not_awaited()
