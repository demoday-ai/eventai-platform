"""Async LLM client for OpenRouter API."""

import json
import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

FALLBACK_MODEL = "anthropic/claude-sonnet-4-20250514"
TIMEOUT = 120.0
MAX_RETRIES = 3


async def send_chat_completion(
    system_prompt: str,
    user_prompt: str,
    json_mode: bool = True,
    model: str | None = None,
    messages: list[dict] | None = None,
) -> dict | str:
    """Send a chat completion request to OpenRouter API.

    Returns parsed JSON dict if json_mode=True, otherwise raw string.
    Retries up to MAX_RETRIES with exponential backoff.
    Falls back to FALLBACK_MODEL on model-specific errors.

    If `messages` is provided, it is used as-is (with system prepended).
    Otherwise, a single user message is constructed from `user_prompt`.
    """
    model = model or settings.openrouter_model
    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "Content-Type": "application/json",
    }

    if messages is not None:
        all_messages = [{"role": "system", "content": system_prompt}] + messages
    else:
        all_messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

    payload = {
        "model": model,
        "messages": all_messages,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}

    import asyncio

    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                response = await client.post(
                    f"{settings.openrouter_base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()

            content = data["choices"][0]["message"]["content"]
            logger.info(
                "LLM response: model=%s tokens_in=%s tokens_out=%s",
                data.get("model", model),
                data.get("usage", {}).get("prompt_tokens"),
                data.get("usage", {}).get("completion_tokens"),
            )

            if json_mode:
                return json.loads(content)
            return content

        except (httpx.HTTPStatusError, httpx.TimeoutException, json.JSONDecodeError) as e:
            last_error = e
            logger.warning(
                "LLM attempt %d/%d failed: %s", attempt + 1, MAX_RETRIES, e
            )

            # On model-specific errors (e.g. 429, 503), try fallback
            if attempt == 1 and model != FALLBACK_MODEL:
                logger.info("Switching to fallback model: %s", FALLBACK_MODEL)
                payload["model"] = FALLBACK_MODEL

            if attempt < MAX_RETRIES - 1:
                wait = 2 ** (attempt + 1)
                await asyncio.sleep(wait)

    raise RuntimeError(f"LLM failed after {MAX_RETRIES} attempts: {last_error}")


async def send_chat_with_tools(
    system_prompt: str,
    messages: list[dict],
    tools: list[dict],
    model: str | None = None,
) -> dict:
    """Send chat completion with tool definitions.

    Returns dict with:
      - "type": "text" | "tool_call"
      - "content": str (if text)
      - "tool_name": str (if tool_call)
      - "tool_args": dict (if tool_call)
    """
    model = model or settings.openrouter_model
    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "Content-Type": "application/json",
    }

    all_messages = [{"role": "system", "content": system_prompt}] + messages

    payload = {
        "model": model,
        "messages": all_messages,
        "tools": tools,
        "tool_choice": "auto",
    }

    import asyncio

    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                response = await client.post(
                    f"{settings.openrouter_base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()

            message = data["choices"][0]["message"]
            logger.info(
                "LLM tools response: model=%s tokens_in=%s tokens_out=%s",
                data.get("model", model),
                data.get("usage", {}).get("prompt_tokens"),
                data.get("usage", {}).get("completion_tokens"),
            )

            # Check for tool call
            if message.get("tool_calls"):
                tool_call = message["tool_calls"][0]
                func = tool_call["function"]
                return {
                    "type": "tool_call",
                    "tool_name": func["name"],
                    "tool_args": json.loads(func["arguments"]) if func.get("arguments") else {},
                }

            # Plain text response
            return {
                "type": "text",
                "content": message.get("content", ""),
            }

        except (httpx.HTTPStatusError, httpx.TimeoutException, json.JSONDecodeError) as e:
            last_error = e
            logger.warning(
                "LLM tools attempt %d/%d failed: %s", attempt + 1, MAX_RETRIES, e
            )

            if attempt == 1 and model != FALLBACK_MODEL:
                logger.info("Switching to fallback model: %s", FALLBACK_MODEL)
                payload["model"] = FALLBACK_MODEL

            if attempt < MAX_RETRIES - 1:
                wait = 2 ** (attempt + 1)
                await asyncio.sleep(wait)

    raise RuntimeError(f"LLM tools failed after {MAX_RETRIES} attempts: {last_error}")
