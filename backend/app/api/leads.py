"""Lead capture API for landing page contact form."""

import logging
from datetime import datetime

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/leads", tags=["leads"])


class LeadCreate(BaseModel):
    name: str
    email: str
    telegram: str | None = None
    phone: str | None = None
    event_type: str
    message: str = ""


class LeadResponse(BaseModel):
    success: bool
    message: str


EVENT_TYPE_LABELS = {
    "demoday": "Demo Day / Pitch Day",
    "conference": "Конференция",
    "hackathon": "Хакатон",
    "exhibition": "Выставка / Ярмарка",
    "other": "Другое",
}


@router.post("", response_model=LeadResponse)
async def create_lead(lead: LeadCreate) -> LeadResponse:
    """Receive lead from landing page and send to team Telegram chat."""

    event_label = EVENT_TYPE_LABELS.get(lead.event_type, lead.event_type)

    # Format message for Telegram
    text = f"🎯 <b>Новая заявка с лендинга</b>\n\n👤 <b>Имя:</b> {lead.name}\n📧 <b>Email:</b> {lead.email}\n"

    if lead.telegram:
        text += f"💬 <b>Telegram:</b> {lead.telegram}\n"

    if lead.phone:
        text += f"📞 <b>Телефон:</b> {lead.phone}\n"

    text += f"📅 <b>Тип события:</b> {event_label}\n"

    if lead.message:
        text += f"💭 <b>Сообщение:</b>\n{lead.message}\n"

    text += f"\n🕐 {datetime.now().strftime('%d.%m.%Y %H:%M')}"

    # Send to Telegram (use team_bot_token if available, otherwise fall back to bot_token)
    bot_token = settings.team_bot_token or settings.bot_token
    if not bot_token or not settings.team_chat_id:
        logger.warning("Lead received but Telegram not configured: %s", lead.email)
        return LeadResponse(success=True, message="Lead saved (Telegram not configured)")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://api.telegram.org/bot{bot_token}/sendMessage",
                json={
                    "chat_id": settings.team_chat_id,
                    "text": text,
                    "parse_mode": "HTML",
                },
                timeout=10.0,
            )
            response.raise_for_status()
            logger.info("Lead sent to Telegram: %s", lead.email)
            return LeadResponse(success=True, message="Lead sent to team")
    except httpx.HTTPError as e:
        logger.error("Failed to send lead to Telegram: %s", e)
        raise HTTPException(status_code=500, detail="Failed to send notification")
