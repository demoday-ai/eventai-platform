"""LLM configuration API endpoints."""

import logging
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_session
from app.models.app_settings import AppSettings
from app.models.llm_api_key import LlmApiKey
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/llm", tags=["LLM Config"])


# Available models with pricing
AVAILABLE_MODELS = [
    {
        "id": "openai/gpt-5.1",
        "name": "GPT-5.1",
        "input_price": 1.25,
        "output_price": 10.0,
        "context": 400000,
        "tier": "flagship",
    },
    {
        "id": "openai/gpt-5-mini",
        "name": "GPT-5-Mini",
        "input_price": 0.25,
        "output_price": 2.0,
        "context": 400000,
        "tier": "recommended",
    },
    {
        "id": "openai/gpt-4o-mini",
        "name": "GPT-4o-Mini",
        "input_price": 0.15,
        "output_price": 0.60,
        "context": 128000,
        "tier": "economy",
    },
    {
        "id": "deepseek/deepseek-chat",
        "name": "DeepSeek Chat",
        "input_price": 0.14,
        "output_price": 0.28,
        "context": 64000,
        "tier": "economy",
    },
]


class ApiKeyCreate(BaseModel):
    api_key: str


class ApiKeyResponse(BaseModel):
    id: str
    key_suffix: str
    is_active: bool
    fail_count: int
    failed_at: str | None
    last_success_at: str | None
    created_at: str


class ModelUpdate(BaseModel):
    model_id: str


@router.get("/models")
async def get_available_models():
    """Get list of available LLM models with pricing."""
    return {"models": AVAILABLE_MODELS}


@router.get("/model")
async def get_current_model(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Get currently selected LLM model."""
    result = await session.execute(
        select(AppSettings).where(AppSettings.key == "llm_model")
    )
    setting = result.scalar_one_or_none()

    if not setting:
        # Return default from config
        from app.config import settings
        return {"model_id": settings.openrouter_model}

    return {"model_id": setting.value}


@router.patch("/model")
async def update_model(
    data: ModelUpdate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Update LLM model selection."""
    # Validate model exists
    valid_models = {m["id"] for m in AVAILABLE_MODELS}
    if data.model_id not in valid_models:
        raise HTTPException(status_code=400, detail="Invalid model ID")

    result = await session.execute(
        select(AppSettings).where(AppSettings.key == "llm_model")
    )
    setting = result.scalar_one_or_none()

    if setting:
        setting.value = data.model_id
    else:
        setting = AppSettings(
            key="llm_model",
            value=data.model_id,
            description="Currently selected LLM model",
        )
        session.add(setting)

    await session.commit()

    logger.info("LLM model updated to %s by user %s", data.model_id, user.id)

    return {"model_id": data.model_id}


@router.get("/keys")
async def get_api_keys(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Get all LLM API keys with status."""
    # Sync key stats from memory to DB before fetching
    from app.services.core.llm_client import get_key_manager, sync_key_stats_to_db
    await sync_key_stats_to_db(session)

    result = await session.execute(select(LlmApiKey).where(LlmApiKey.is_active))
    keys = result.scalars().all()

    # Get live stats from KeyManager
    key_manager = get_key_manager()
    stats = key_manager.get_stats()

    # Merge DB data with live stats
    response = []
    for key_obj in keys:
        # Find matching live stats
        live_stat = next(
            (s for s in stats["keys"] if key_obj.api_key.endswith(s["suffix"])),
            None
        )

        response.append({
            "id": str(key_obj.id),
            "key_suffix": key_obj.key_suffix,
            "is_active": key_obj.is_active,
            "fail_count": live_stat["fail_count"] if live_stat else key_obj.fail_count,
            "available": live_stat["available"] if live_stat else True,
            "cooldown_remaining": live_stat.get("cooldown_remaining", 0) if live_stat else 0,
            "failed_at": key_obj.failed_at.isoformat() if key_obj.failed_at else None,
            "last_success_at": key_obj.last_success_at.isoformat() if key_obj.last_success_at else None,
            "created_at": key_obj.created_at.isoformat(),
        })

    return {"keys": response}


@router.post("/keys")
async def add_api_key(
    data: ApiKeyCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Add new LLM API key."""
    api_key = data.api_key.strip()

    if not api_key.startswith("sk-"):
        raise HTTPException(status_code=400, detail="Invalid API key format")

    # Check if key already exists
    result = await session.execute(
        select(LlmApiKey).where(LlmApiKey.api_key == api_key)
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Key already exists")

    key_suffix = api_key[-8:]

    new_key = LlmApiKey(
        api_key=api_key,
        key_suffix=key_suffix,
        is_active=True,
        fail_count=0,
    )
    session.add(new_key)
    await session.commit()
    await session.refresh(new_key)

    logger.info("LLM API key added: ...%s by user %s", key_suffix, user.id)

    # Reload KeyManager to pick up new key
    from app.services.core.llm_client import get_key_manager
    get_key_manager()._initialized = False

    return {
        "id": str(new_key.id),
        "key_suffix": key_suffix,
        "created_at": new_key.created_at.isoformat(),
    }


@router.delete("/keys/{key_id}")
async def delete_api_key(
    key_id: UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Delete LLM API key."""
    result = await session.execute(
        select(LlmApiKey).where(LlmApiKey.id == key_id)
    )
    key_obj = result.scalar_one_or_none()

    if not key_obj:
        raise HTTPException(status_code=404, detail="Key not found")

    # Check if this is the last active key
    result = await session.execute(
        select(LlmApiKey).where(LlmApiKey.is_active)
    )
    active_keys = result.scalars().all()

    if len(active_keys) <= 1:
        raise HTTPException(status_code=400, detail="Cannot delete last active key")

    await session.delete(key_obj)
    await session.commit()

    logger.info("LLM API key deleted: ...%s by user %s", key_obj.key_suffix, user.id)

    # Reload KeyManager
    from app.services.core.llm_client import get_key_manager
    get_key_manager()._initialized = False

    return {"status": "deleted"}


@router.post("/keys/check")
async def check_all_keys(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Manually trigger health check for all keys."""
    from app.services.core.llm_client import check_api_health

    result = await check_api_health()
    logger.info("Manual LLM health check triggered by user %s", user.id)

    # Update last_success_at in DB for successful keys
    for key_result in result.get("keys", []):
        if key_result["status"] == "ok":
            key_suffix = key_result["key_suffix"]
            stmt = select(LlmApiKey).where(LlmApiKey.key_suffix == key_suffix)
            key_obj = (await session.execute(stmt)).scalar_one_or_none()
            if key_obj:
                key_obj.last_success_at = datetime.now(timezone.utc)
                key_obj.fail_count = 0
                key_obj.failed_at = None

    await session.commit()

    return result
