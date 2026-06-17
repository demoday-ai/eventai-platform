import logging

from src.schemas.tools import ProfileTurn
from src.services.platform_client import PlatformClient

logger = logging.getLogger(__name__)

_SAFE_REPLY = {"action": "reply", "message": "Расскажите подробнее о ваших интересах."}


async def chat_for_profile(
    platform: PlatformClient,
    system_prompt: str,
    conversation: list[dict],
) -> dict:
    """One turn of profiling dialogue (structured output via ProfileTurn).

    Returns dict with:
    - action: "reply" (continue dialog) or "profile" (profile extracted)
    - message: reply text (if action=reply)
    - interests, goals, summary: extracted profile (if action=profile)
    - company, position, business_objectives: business fields (if business)

    On any model/parse error returns a safe reply - NEVER echoes raw model
    output to the user (that previously leaked JSON when a model wrapped its
    json_object response in ```json fences).
    """
    try:
        messages = [{"role": "system", "content": system_prompt}] + conversation
        result: ProfileTurn = await platform.structured_completion(messages, ProfileTurn)
        data = result.model_dump()
        if data.get("action") not in ("reply", "profile"):
            data["action"] = "reply"
        if data["action"] == "reply" and not data.get("message"):
            data["message"] = _SAFE_REPLY["message"]
        return data
    except Exception as e:
        logger.warning("Profiling structured output failed: %s", e)
        return dict(_SAFE_REPLY)


def normalize_profile_display(
    interests: list[str],
    goals: list[str],
    summary: str,
) -> tuple[list[str], str]:
    """Clean up LLM-extracted profile for user-facing display.

    - Dedupe interests; drop a bare parent tag ("CV") when subtags
      ("CV (детекция объектов)") are present — the parent adds noise.
    - Strip summary lines that merely repeat a goal ("Цель: ...") since
      goals are rendered separately.
    """
    # Dedupe preserving order
    seen: set[str] = set()
    deduped: list[str] = []
    for tag in interests:
        t = tag.strip()
        if t and t not in seen:
            seen.add(t)
            deduped.append(t)

    # Drop bare parents that have subtags like "Parent (...)"
    parents_with_subtags = {
        t.split("(")[0].strip() for t in deduped if "(" in t
    }
    cleaned_interests = [
        t for t in deduped
        if not ("(" not in t and t in parents_with_subtags)
    ]

    # Strip goal-duplicating lines from summary
    goal_set = {g.strip().lower() for g in goals}
    kept_lines: list[str] = []
    for line in (summary or "").splitlines():
        stripped = line.strip()
        body = stripped
        for prefix in ("Цель:", "Цели:", "Goal:", "Goals:"):
            if body.startswith(prefix):
                body = body[len(prefix):].strip()
                break
        if stripped and body.lower() in goal_set:
            continue
        kept_lines.append(line)
    clean_summary = "\n".join(kept_lines).strip()

    return cleaned_interests, clean_summary


def build_profile_text(
    selected_tags: list[str] | None,
    keywords: list[str] | None,
    nl_summary: str | None,
    company: str | None = None,
    business_objectives: list[str] | None = None,
    raw_text: str | None = None,
) -> str:
    """Build text for embedding from profile data."""
    parts: list[str] = []
    if nl_summary:
        parts.append(nl_summary)
    if selected_tags:
        parts.append(f"Интересы: {', '.join(selected_tags)}")
    if keywords:
        parts.append(f"Ключевые слова: {', '.join(keywords)}")
    if company:
        parts.append(f"Компания: {company}")
    if business_objectives:
        parts.append(f"Бизнес-цели: {', '.join(business_objectives)}")
    if raw_text:
        parts.append(raw_text[:500])

    return ". ".join(parts) if parts else "Интерес к AI проектам"
