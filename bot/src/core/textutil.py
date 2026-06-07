"""Shared text utilities for user-facing rendering."""


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
