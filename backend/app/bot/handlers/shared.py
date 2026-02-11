"""Shared helpers and formatters for bot handlers."""

import logging

from app.database import async_session
from app.models.role import RoleCode
from app.services.core import user_service

logger = logging.getLogger(__name__)

MAX_MESSAGE_LEN = 4096


async def check_guest_or_business(telegram_user_id: str) -> tuple | None:
    """Check if user has guest or business role. Returns (user, event, role_code) or None."""
    async with async_session() as session:
        user = await user_service.get_user_by_telegram_id(session, telegram_user_id)
        if not user:
            return None
        event = await user_service.get_current_event(session)
        if not event:
            return None
        role_info = await user_service.get_user_role_with_info(session, user.id, event.id)
        if not role_info or role_info.code not in (RoleCode.GUEST.value, RoleCode.BUSINESS.value):
            return None
        return user, event, role_info.code


def truncate(text: str, limit: int) -> str:
    """Truncate text at sentence boundary, fallback to word boundary."""
    if not text or len(text) <= limit:
        return text
    chunk = text[:limit]
    for sep in (". ", "! ", "? ", ".\n"):
        pos = chunk.rfind(sep)
        if pos > limit // 3:
            return chunk[: pos + 1]
    pos = chunk.rfind(" ")
    if pos > limit // 3:
        return chunk[:pos] + "..."
    return chunk + "..."


def escape_markdown(text: str) -> str:
    """Escape Markdown special characters (idempotent — won't double-escape)."""
    if not text:
        return ""
    for char in ["*", "_", "`", "[", "]", "(", ")"]:
        # Remove existing escapes first, then re-escape uniformly
        text = text.replace("\\" + char, char)
        text = text.replace(char, "\\" + char)
    return text


def format_recommendations(data: dict) -> list[str]:
    """Format must-visit recommendations into message parts (respecting 4096 char limit)."""
    messages = []
    must_recs = data.get("must_visit", [])
    total = data.get("total", len(must_recs))

    must_text = f"*Твоя программа ({len(must_recs)} из {total}):*\n\n"
    prev_rooms: set[int] = set()
    for rec in must_recs:
        title = escape_markdown(rec["title"])
        summary = escape_markdown(truncate(rec["summary"], 120) if rec["summary"] else "")
        room_info = f"Зал {rec['room_number']}" if rec.get("room_number") else ""
        tags_str = ", ".join(rec.get("tags", [])[:3])

        conflict = ""
        room_num = rec.get("room_number")
        if room_num and room_num in prev_rooms:
            conflict = "\n   _пересекается с проектом выше_"
        if room_num:
            prev_rooms.add(room_num)

        entry = f"*{rec['rank']}.* *{title}*\n   {room_info} · {tags_str}\n   → {summary}{conflict}\n\n"
        must_text += entry

    must_text += (
        "Напиши мне:\n"
        "• номер — подробности\n"
        "• «сравни 1 и 3» — матрица\n"
        "• «вопросы к 2» — подготовлю Q&A\n"
        "• «хочу другое» — изменю подборку"
    )

    if len(must_text) > MAX_MESSAGE_LEN:
        mid = len(must_recs) // 2
        part1 = f"*Твоя программа ({len(must_recs)} из {total}):*\n\n"
        part2 = ""
        prev_rooms_split: set[int] = set()
        for i, rec in enumerate(must_recs):
            title = escape_markdown(rec["title"])
            summary = escape_markdown(truncate(rec["summary"], 120) if rec["summary"] else "")
            room_info = f"Зал {rec['room_number']}" if rec.get("room_number") else ""
            tags_str = ", ".join(rec.get("tags", [])[:3])
            conflict = ""
            room_num = rec.get("room_number")
            if room_num and room_num in prev_rooms_split:
                conflict = "\n   _пересекается с проектом выше_"
            if room_num:
                prev_rooms_split.add(room_num)
            entry = f"*{rec['rank']}.* *{title}*\n   {room_info} · {tags_str}\n   → {summary}{conflict}\n\n"
            if i < mid:
                part1 += entry
            else:
                part2 += entry
        messages.append(part1)
        if part2:
            messages.append(part2)
    else:
        messages.append(must_text)

    return messages


def format_if_time(data: dict) -> list[str]:
    """Format if-time recommendations into message parts."""
    messages = []
    if_time_text = "*Дополнительно:*\n\n"
    for rec in data.get("if_time", []):
        title = escape_markdown(rec["title"])
        summary = escape_markdown(truncate(rec["summary"], 150) if rec["summary"] else "")
        room_info = f"Зал {rec['room_number']}" if rec.get("room_number") else ""
        tags_str = ", ".join(rec.get("tags", [])[:3])

        score = int(rec.get("relevance_score", 0))
        entry = f"*{rec['rank']}. {title}* — {score}%\n{summary}\n{room_info} · {tags_str}\n\n"
        if_time_text += entry

    if len(if_time_text) > MAX_MESSAGE_LEN:
        if_recs = data.get("if_time", [])
        mid = len(if_recs) // 2
        part1 = "*Дополнительно:*\n\n"
        part2 = ""
        for i, rec in enumerate(if_recs):
            title = escape_markdown(rec["title"])
            summary = escape_markdown(truncate(rec["summary"], 150) if rec["summary"] else "")
            room_info = f"Зал {rec['room_number']}" if rec.get("room_number") else ""
            tags_str = ", ".join(rec.get("tags", [])[:3])
            entry = f"*{rec['rank']}. {title}*\n{summary}\n{room_info} · {tags_str}\n\n"
            if i < mid:
                part1 += entry
            else:
                part2 += entry
        messages.append(part1)
        if part2:
            messages.append(part2)
    else:
        messages.append(if_time_text)

    return messages


def get_conversation(context) -> list[dict]:
    """Get conversation history from context."""
    return context.user_data.get("nl_conversation", [])


def add_to_conversation(context, role: str, content: str) -> list[dict]:
    """Add message to conversation history and return it."""
    conv = get_conversation(context)
    conv.append({"role": role, "content": content})
    context.user_data["nl_conversation"] = conv
    return conv
