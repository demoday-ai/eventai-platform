"""Shared text utilities for user-facing rendering."""

import json
import re


def loads_json_lenient(content: str) -> dict | list:
    """Parse JSON from an LLM response, tolerating markdown ```json fences and
    surrounding prose. Some models (e.g. deepseek-v4) wrap json_object output in
    ```json ... ``` despite response_format, which breaks a bare json.loads.

    Raises json.JSONDecodeError if no JSON can be recovered.
    """
    if not content or not content.strip():
        raise json.JSONDecodeError("empty content", content or "", 0)
    s = content.strip()
    # Strip a leading ```json / ``` fence and trailing ```.
    if s.startswith("```"):
        s = re.sub(r"^```[a-zA-Z0-9]*\s*", "", s)
        s = re.sub(r"\s*```$", "", s).strip()
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        # Last resort: grab the first {...} or [...] block in the text.
        m = re.search(r"(\{.*\}|\[.*\])", s, re.DOTALL)
        if m:
            return json.loads(m.group(1))
        raise


def smart_truncate(text: str, limit: int) -> str:
    """Cut text to <= limit chars without breaking words.

    Prefers the last sentence boundary near the limit, falls back to the
    last whitespace, never cuts mid-word. Appends an ellipsis when the
    text was actually truncated.
    """
    if not text or len(text) <= limit:
        return text or ""
    cut = text[:limit]
    # Prefer sentence boundary if it is reasonably close to the limit
    for sep in (". ", "! ", "? ", ".\n", "!\n", "?\n", ";\n"):
        idx = cut.rfind(sep)
        if idx >= limit - 200 and idx > 0:
            return cut[: idx + 1].rstrip() + " ..."
    # Fall back to last whitespace
    idx = cut.rfind(" ")
    if idx > 0:
        return cut[:idx].rstrip() + " ..."
    return cut.rstrip() + "..."


_OBJECTIVE_RU = {
    "investment": "инвестиции",
    "hiring": "найм",
    "partnership": "партнёрство",
    "technology": "технологии и внедрение",
}


def objectives_ru(codes) -> str:
    """Human-readable RU labels for business_objectives codes (technology -> текст)."""
    return ", ".join(_OBJECTIVE_RU.get(c, c) for c in (codes or []))
