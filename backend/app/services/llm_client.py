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
) -> dict | str:
    """Send a chat completion request to OpenRouter API.

    Returns parsed JSON dict if json_mode=True, otherwise raw string.
    Retries up to MAX_RETRIES with exponential backoff.
    Falls back to FALLBACK_MODEL on model-specific errors.
    """
    model = model or settings.openrouter_model
    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
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
