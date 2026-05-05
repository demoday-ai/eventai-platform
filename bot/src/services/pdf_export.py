"""PDF export for personalized Demo Day recommendations."""

import io
from pathlib import Path

from fpdf import FPDF
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.project import Project
from src.models.recommendation import Recommendation
from src.models.room import Room
from src.models.schedule_slot import ScheduleSlot

FONTS_DIR = Path(__file__).resolve().parent.parent.parent / "fonts"
DESC_LIMIT = 600  # truncate long descriptions but cut on word boundary


def _smart_truncate(text: str, limit: int) -> str:
    """Cut text to <= limit chars, prefer the last sentence boundary,
    fall back to last whitespace, never mid-word. Adds an ellipsis
    when truncation actually happened.
    """
    if not text or len(text) <= limit:
        return text or ""
    cut = text[:limit]
    # Prefer punctuation
    for sep in (". ", "! ", "? ", ".\n", "!\n", "?\n", ";\n"):
        idx = cut.rfind(sep)
        if idx >= limit - 200:  # require the boundary to be reasonably close to limit
            return cut[: idx + 1].rstrip() + " ..."
    # Fall back to last whitespace
    idx = cut.rfind(" ")
    if idx > 0:
        return cut[:idx].rstrip() + " ..."
    return cut.rstrip() + " ..."


async def generate_recommendations_pdf(
    recs: list[Recommendation],
    projects: list[Project],
    user_name: str = "Участник",
    event_name: str = "Demo Day",
    db: AsyncSession | None = None,
) -> io.BytesIO:
    """Build a PDF with the ranked recommendation list.

    Includes time/room info and smart-truncated description (no mid-word cuts).
    """
    pdf = FPDF()
    pdf.add_font("DejaVu", "", str(FONTS_DIR / "DejaVuSans.ttf"), uni=True)
    pdf.add_font("DejaVu", "B", str(FONTS_DIR / "DejaVuSans-Bold.ttf"), uni=True)
    pdf.add_page()

    pdf.set_font("DejaVu", "B", 16)
    pdf.cell(0, 10, f"Программа {event_name}", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("DejaVu", "", 10)
    pdf.cell(0, 8, f"Подготовлено для: {user_name}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    projects_by_id = {p.id: p for p in projects}

    # Pre-load slot info for any rec that has slot_id
    slots_by_rec_id: dict = {}
    if db is not None:
        slot_ids = [r.slot_id for r in recs if r.slot_id]
        if slot_ids:
            rows = await db.execute(
                select(ScheduleSlot, Room.name.label("room_name"))
                .join(Room, ScheduleSlot.room_id == Room.id)
                .where(ScheduleSlot.id.in_(slot_ids))
            )
            for row in rows.all():
                slots_by_rec_id[row[0].id] = (row[0], row.room_name)

    for rec in recs:
        project = projects_by_id.get(rec.project_id)
        if not project:
            continue

        # Title with rank + (если успеете)
        marker = "  (если успеете)" if rec.category == "if_time" else ""
        pdf.set_font("DejaVu", "B", 12)
        pdf.multi_cell(
            0, 7, f"#{rec.rank}  {project.title}{marker}",
            new_x="LMARGIN", new_y="NEXT",
        )
        pdf.ln(1)

        # Time and Room go on SEPARATE multi_cell calls. A single combined
        # 'Время: ... Зал: ...' line breaks badly when room name is long
        # (renders 'Зал' before 'Время' or pulls in description fragments).
        if rec.slot_id and rec.slot_id in slots_by_rec_id:
            slot, room_name = slots_by_rec_id[rec.slot_id]
            time_str = slot.start_time.strftime("%H:%M")
            end_str = slot.end_time.strftime("%H:%M")
            pdf.set_font("DejaVu", "", 9)
            pdf.multi_cell(
                0, 5, f"Время:  {time_str}–{end_str}",
                new_x="LMARGIN", new_y="NEXT",
            )
            pdf.multi_cell(
                0, 5, f"Зал:    {room_name}",
                new_x="LMARGIN", new_y="NEXT",
            )
        pdf.ln(2)

        # Description (smart-truncated, never mid-word)
        if project.description:
            desc = _smart_truncate(project.description, DESC_LIMIT)
            pdf.set_font("DejaVu", "", 10)
            pdf.multi_cell(0, 6, desc, new_x="LMARGIN", new_y="NEXT")
            pdf.ln(1)

        # Meta block (tags, stack, author, contact) on its own line each
        meta_lines = []
        if project.tags:
            meta_lines.append(f"Теги:    {', '.join(str(t) for t in project.tags)}")
        if project.tech_stack:
            meta_lines.append(f"Стек:    {', '.join(str(t) for t in project.tech_stack)}")
        if project.author:
            meta_lines.append(f"Автор:   {project.author}")
        if project.telegram_contact:
            meta_lines.append(f"Контакт: {project.telegram_contact}")
        if meta_lines:
            pdf.set_font("DejaVu", "", 9)
            for line in meta_lines:
                pdf.multi_cell(0, 5, line, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(5)

    buf = io.BytesIO()
    pdf.output(buf)
    buf.seek(0)
    return buf
