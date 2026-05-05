#!/usr/bin/env python3
"""Generate invite_code for experts that don't have one yet.

Idempotent: only fills experts where invite_code IS NULL. Prints a
ready-to-share deep link for each updated expert.

Usage:
    docker compose exec bot python -m scripts.generate_expert_codes
"""
import asyncio
import logging
import os
import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

os.environ.setdefault("BOT_TOKEN", "expert-codes")

from sqlalchemy import select

from src.core.database import async_session
from src.models.expert import Expert

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


async def main() -> None:
    bot_username = os.environ.get("BOT_USERNAME", "demoday_ai_talent_hub_test_bot")

    async with async_session() as db:
        result = await db.execute(
            select(Expert).where(Expert.invite_code.is_(None)).order_by(Expert.name)
        )
        experts = result.scalars().all()

        if not experts:
            logger.info("All experts already have invite codes. Nothing to do.")
            return

        logger.info("Generating codes for %d experts...\n", len(experts))

        for exp in experts:
            code = f"exp_{secrets.token_urlsafe(8)}"
            exp.invite_code = code

        await db.commit()

        print("Expert invite links (share with each expert privately):\n")
        for exp in experts:
            link = f"https://t.me/{bot_username}?start=expert_{exp.invite_code}"
            print(f"  {exp.name}: {link}")
            print(f"    or paste code in bot: {exp.invite_code}\n")


if __name__ == "__main__":
    asyncio.run(main())
