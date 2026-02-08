"""Async LLM client for OpenRouter API with multi-key rotation."""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

FALLBACK_MODEL = "anthropic/claude-sonnet-4-20250514"
TIMEOUT = 120.0
MAX_RETRIES = 3
KEY_COOLDOWN_SECONDS = 60  # Time to wait before retrying a failed key


@dataclass
class KeyState:
    """Track state of an API key."""

    key: str
    failed_at: float | None = None
    fail_count: int = 0
    last_success: float = field(default_factory=time.time)

    def is_available(self) -> bool:
        """Check if key is available (not in cooldown)."""
        if self.failed_at is None:
            return True
        return time.time() - self.failed_at > KEY_COOLDOWN_SECONDS

    def mark_failed(self) -> None:
        """Mark key as failed, entering cooldown."""
        self.failed_at = time.time()
        self.fail_count += 1
        logger.warning(
            "API key marked failed: ...%s (fail_count=%d)",
            self.key[-8:],
            self.fail_count,
        )

    def mark_success(self) -> None:
        """Mark key as successful, reset cooldown."""
        self.failed_at = None
        self.last_success = time.time()


class KeyManager:
    """Manage multiple API keys with rotation and failover."""

    def __init__(self) -> None:
        self._keys: list[KeyState] = []
        self._current_index: int = 0
        self._initialized: bool = False

    def _ensure_initialized(self) -> None:
        """Initialize keys from settings (lazy load)."""
        if self._initialized:
            return

        keys = settings.api_keys
        if not keys:
            # Fallback to single key
            if settings.openrouter_api_key:
                keys = [settings.openrouter_api_key]
            else:
                raise ValueError("No API keys configured")

        self._keys = [KeyState(key=k) for k in keys]
        self._initialized = True
        logger.info("KeyManager initialized with %d API keys", len(self._keys))

    def get_next_key(self) -> str:
        """Get next available API key with round-robin rotation."""
        self._ensure_initialized()

        if not self._keys:
            raise ValueError("No API keys configured")

        # Try to find an available key using round-robin
        attempts = 0

        while attempts < len(self._keys):
            key_state = self._keys[self._current_index]
            self._current_index = (self._current_index + 1) % len(self._keys)

            if key_state.is_available():
                logger.debug("Using API key: ...%s", key_state.key[-8:])
                return key_state.key

            attempts += 1

        # All keys in cooldown - use the one that failed longest ago
        oldest = min(self._keys, key=lambda k: k.failed_at or 0)
        logger.warning(
            "All keys in cooldown, using oldest failed: ...%s",
            oldest.key[-8:],
        )
        return oldest.key

    def mark_key_failed(self, key: str) -> None:
        """Mark a key as failed."""
        self._ensure_initialized()
        for key_state in self._keys:
            if key_state.key == key:
                key_state.mark_failed()
                return

    def mark_key_success(self, key: str) -> None:
        """Mark a key as successful."""
        self._ensure_initialized()
        for key_state in self._keys:
            if key_state.key == key:
                key_state.mark_success()
                return

    def get_stats(self) -> dict:
        """Get statistics about all keys."""
        self._ensure_initialized()
        return {
            "total_keys": len(self._keys),
            "available_keys": sum(1 for k in self._keys if k.is_available()),
            "keys": [
                {
                    "suffix": k.key[-8:],
                    "available": k.is_available(),
                    "fail_count": k.fail_count,
                    "cooldown_remaining": (
                        max(0, KEY_COOLDOWN_SECONDS - (time.time() - k.failed_at))
                        if k.failed_at
                        else 0
                    ),
                }
                for k in self._keys
            ],
        }


# Global key manager instance
_key_manager = KeyManager()


def get_key_manager() -> KeyManager:
    """Get the global key manager instance."""
    return _key_manager


async def send_chat_completion(
    system_prompt: str,
    user_prompt: str,
    json_mode: bool = True,
    model: str | None = None,
    messages: list[dict] | None = None,
) -> dict | str:
    """Send a chat completion request to OpenRouter API.

    Returns parsed JSON dict if json_mode=True, otherwise raw string.
    Retries up to MAX_RETRIES with key rotation and exponential backoff.
    Falls back to FALLBACK_MODEL on model-specific errors.

    If `messages` is provided, it is used as-is (with system prepended).
    Otherwise, a single user message is constructed from `user_prompt`.
    """
    model = model or settings.openrouter_model
    current_model = model

    if messages is not None:
        all_messages = [{"role": "system", "content": system_prompt}] + messages
    else:
        all_messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

    payload = {
        "model": current_model,
        "messages": all_messages,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}

    last_error = None
    keys_tried: set[str] = set()

    for attempt in range(MAX_RETRIES):
        # Get next available key
        api_key = _key_manager.get_next_key()
        keys_tried.add(api_key)

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

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
                "LLM response: model=%s tokens_in=%s tokens_out=%s key=...%s",
                data.get("model", current_model),
                data.get("usage", {}).get("prompt_tokens"),
                data.get("usage", {}).get("completion_tokens"),
                api_key[-8:],
            )

            # Mark key as successful
            _key_manager.mark_key_success(api_key)

            if json_mode:
                return json.loads(content)
            return content

        except httpx.HTTPStatusError as e:
            last_error = e
            status = e.response.status_code

            logger.warning(
                "LLM attempt %d/%d failed: HTTP %d, key=...%s",
                attempt + 1,
                MAX_RETRIES,
                status,
                api_key[-8:],
            )

            # Rate limit or auth error - mark key as failed
            if status in (401, 429, 503):
                _key_manager.mark_key_failed(api_key)

            # On model-specific errors, try fallback model
            if attempt == 1 and current_model != FALLBACK_MODEL:
                logger.info("Switching to fallback model: %s", FALLBACK_MODEL)
                current_model = FALLBACK_MODEL
                payload["model"] = current_model

            if attempt < MAX_RETRIES - 1:
                wait = 2 ** (attempt + 1)
                await asyncio.sleep(wait)

        except (httpx.TimeoutException, json.JSONDecodeError) as e:
            last_error = e
            logger.warning(
                "LLM attempt %d/%d failed: %s, key=...%s",
                attempt + 1,
                MAX_RETRIES,
                type(e).__name__,
                api_key[-8:],
            )

            if attempt < MAX_RETRIES - 1:
                wait = 2 ** (attempt + 1)
                await asyncio.sleep(wait)

    raise RuntimeError(
        f"LLM failed after {MAX_RETRIES} attempts (keys tried: {len(keys_tried)}): {last_error}"
    )


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
    current_model = model

    all_messages = [{"role": "system", "content": system_prompt}] + messages

    payload = {
        "model": current_model,
        "messages": all_messages,
        "tools": tools,
        "tool_choice": "auto",
    }

    last_error = None
    keys_tried: set[str] = set()

    for attempt in range(MAX_RETRIES):
        api_key = _key_manager.get_next_key()
        keys_tried.add(api_key)

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

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
                "LLM tools response: model=%s tokens_in=%s tokens_out=%s key=...%s",
                data.get("model", current_model),
                data.get("usage", {}).get("prompt_tokens"),
                data.get("usage", {}).get("completion_tokens"),
                api_key[-8:],
            )

            _key_manager.mark_key_success(api_key)

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

        except httpx.HTTPStatusError as e:
            last_error = e
            status = e.response.status_code

            logger.warning(
                "LLM tools attempt %d/%d failed: HTTP %d, key=...%s",
                attempt + 1,
                MAX_RETRIES,
                status,
                api_key[-8:],
            )

            if status in (401, 429, 503):
                _key_manager.mark_key_failed(api_key)

            if attempt == 1 and current_model != FALLBACK_MODEL:
                logger.info("Switching to fallback model: %s", FALLBACK_MODEL)
                current_model = FALLBACK_MODEL
                payload["model"] = current_model

            if attempt < MAX_RETRIES - 1:
                wait = 2 ** (attempt + 1)
                await asyncio.sleep(wait)

        except (httpx.TimeoutException, json.JSONDecodeError) as e:
            last_error = e
            logger.warning(
                "LLM tools attempt %d/%d failed: %s, key=...%s",
                attempt + 1,
                MAX_RETRIES,
                type(e).__name__,
                api_key[-8:],
            )

            if attempt < MAX_RETRIES - 1:
                wait = 2 ** (attempt + 1)
                await asyncio.sleep(wait)

    raise RuntimeError(
        f"LLM tools failed after {MAX_RETRIES} attempts (keys tried: {len(keys_tried)}): {last_error}"
    )


async def check_api_health() -> dict:
    """Check health of all API keys by making a minimal request.

    Returns dict with status of each key.
    """
    results = []

    for key_state in _key_manager._keys:
        key = key_state.key
        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }

        # Minimal request to check if key works
        payload = {
            "model": "openai/gpt-4o-mini",
            "messages": [{"role": "user", "content": "Hi"}],
            "max_tokens": 1,
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{settings.openrouter_base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()

            results.append({
                "key_suffix": key[-8:],
                "status": "ok",
                "available": key_state.is_available(),
            })
            key_state.mark_success()

        except httpx.HTTPStatusError as e:
            results.append({
                "key_suffix": key[-8:],
                "status": "error",
                "error": f"HTTP {e.response.status_code}",
                "available": key_state.is_available(),
            })

        except Exception as e:
            results.append({
                "key_suffix": key[-8:],
                "status": "error",
                "error": str(e),
                "available": key_state.is_available(),
            })

    return {
        "keys": results,
        "total": len(results),
        "healthy": sum(1 for r in results if r["status"] == "ok"),
    }
