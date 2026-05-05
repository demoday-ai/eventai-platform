"""Production smoke test.

Runs inside the bot container against live DB / Redis / OpenRouter.
Feeds a synthetic /start update through the real Dispatcher (with real
middlewares and routers) and verifies that the bot replies without
raising. Cleans up the fake user before and after.

Usage (inside container):
    docker exec demoday-core-bot-1 python -m scripts.smoke
    docker exec demoday-core-bot-1 python -m scripts.smoke --user-id 999000777

Exit codes:
    0 - bot replied successfully
    1 - failure (no reply, exception, DB error, etc.)
"""

from __future__ import annotations

import argparse
import asyncio
import datetime
import random
import sys
import traceback
from collections import deque
from pathlib import Path
from typing import Any, Awaitable, Callable

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from aiogram import BaseMiddleware, Bot, Dispatcher
from aiogram.client.session.base import BaseSession
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.methods import (
    AnswerCallbackQuery,
    DeleteMessage,
    EditMessageText,
    SendMessage,
)
from aiogram.methods.base import TelegramMethod, TelegramType
from aiogram.types import (
    Chat,
    Message,
    TelegramObject,
    UNSET_PARSE_MODE,
    Update,
    User,
)


SMOKE_USER_ID_RANGE = (999_000_000, 999_999_999)


def _pick_user_id(explicit: int | None) -> int:
    if explicit is not None:
        return explicit
    return random.randint(*SMOKE_USER_ID_RANGE)


class _CapturingSession(BaseSession):
    """Records outgoing TelegramMethod calls instead of hitting Telegram."""

    def __init__(self) -> None:
        super().__init__()
        self.captured: deque[TelegramMethod] = deque()

    async def make_request(
        self,
        bot: Bot,
        method: TelegramMethod[TelegramType],
        timeout: Any = UNSET_PARSE_MODE,
    ) -> TelegramType:
        self.captured.append(method)
        if isinstance(method, SendMessage):
            return Message(
                message_id=len(self.captured) + 100,
                date=datetime.datetime.now(),
                text=method.text or "",
                chat=Chat(id=method.chat_id, type="private"),
            )
        if isinstance(method, EditMessageText):
            return Message(
                message_id=method.message_id or 1,
                date=datetime.datetime.now(),
                text=method.text or "",
                chat=Chat(id=method.chat_id, type="private"),
            )
        if isinstance(method, (AnswerCallbackQuery, DeleteMessage)):
            return True  # type: ignore[return-value]
        return True  # type: ignore[return-value]

    async def close(self) -> None:  # noqa: D401
        return None

    async def stream_content(self, *args: Any, **kwargs: Any):  # type: ignore[override]
        raise NotImplementedError


class _SmokeBot(Bot):
    def __init__(self) -> None:
        super().__init__(token="42:TEST", session=_CapturingSession())
        self._me = User(
            id=42,
            is_bot=True,
            first_name="Smoke",
            username="smokebot",
            language_code="ru",
        )

    def captured_methods(self) -> list[TelegramMethod]:
        return list(self.session.captured)  # type: ignore[union-attr]


def _make_message_update(text: str, user_id: int, msg_id: int = 1) -> Update:
    return Update(
        update_id=msg_id,
        message=Message(
            message_id=msg_id,
            date=datetime.datetime.now(),
            text=text,
            chat=Chat(id=user_id, type="private"),
            from_user=User(
                id=user_id,
                is_bot=False,
                first_name="Smoke",
                username=f"smoke_{user_id}",
            ),
        ),
    )


async def _cleanup_user(session_factory: Any, user_id: int) -> None:
    """Best-effort wipe of all rows belonging to the smoke user.

    Uses ON DELETE CASCADE where defined; for tables without CASCADE
    (guest_profiles, recommendations, support_log, etc.) deletes child
    rows explicitly first.
    """
    from sqlalchemy import text as sql_text

    uid = str(user_id)
    async with session_factory() as session:
        for stmt in (
            "DELETE FROM recommendations WHERE user_id IN (SELECT id FROM users WHERE telegram_user_id = :uid)",
            "DELETE FROM guest_profiles WHERE user_id IN (SELECT id FROM users WHERE telegram_user_id = :uid)",
            "DELETE FROM support_log WHERE user_id IN (SELECT id FROM users WHERE telegram_user_id = :uid)",
            "DELETE FROM bot_expert_scores WHERE expert_user_id IN (SELECT id FROM users WHERE telegram_user_id = :uid)",
            "DELETE FROM users WHERE telegram_user_id = :uid",
        ):
            try:
                await session.execute(sql_text(stmt), {"uid": uid})
            except Exception:
                # Tables that don't exist in this schema variant or rows
                # already gone -- skip and continue cleanup.
                await session.rollback()
                continue
        await session.commit()


async def _build_dispatcher() -> tuple[_SmokeBot, Dispatcher, Any]:
    from pydantic import SecretStr
    from sqlalchemy.ext.asyncio import (
        AsyncSession,
        async_sessionmaker,
        create_async_engine,
    )

    from src.core.config import settings
    from src.services.platform_client import PlatformClient

    engine = create_async_engine(settings.database_url, pool_size=2)
    session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    if settings.openrouter_api_key:
        platform = PlatformClient(
            platform_url="https://openrouter.ai/api", master_token="unused"
        )
        platform._token = SecretStr(settings.openrouter_api_key)
    else:
        platform = PlatformClient(
            platform_url=settings.platform_url,
            master_token=settings.master_token or "unused",
        )

    class _Db(BaseMiddleware):
        async def __call__(
            self,
            handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: dict[str, Any],
        ) -> Any:
            async with session_factory() as session:
                data["db"] = session
                try:
                    result = await handler(event, data)
                    await session.commit()
                    return result
                except Exception:
                    await session.rollback()
                    raise

    class _Plat(BaseMiddleware):
        async def __call__(
            self,
            handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: dict[str, Any],
        ) -> Any:
            data["platform"] = platform
            return await handler(event, data)

    bot = _SmokeBot()
    dp = Dispatcher(storage=MemoryStorage())
    dp.message.middleware(_Db())
    dp.message.middleware(_Plat())
    dp.callback_query.middleware(_Db())
    dp.callback_query.middleware(_Plat())

    from src.bot.routers.detail import router as detail_router
    from src.bot.routers.expert import router as expert_router
    from src.bot.routers.fallback import router as fallback_router
    from src.bot.routers.profiling import router as profiling_router
    from src.bot.routers.program import router as program_router
    from src.bot.routers.start import router as start_router
    from src.bot.routers.support import router as support_router

    dp.include_router(start_router)
    dp.include_router(profiling_router)
    dp.include_router(expert_router)
    dp.include_router(detail_router)
    dp.include_router(support_router)
    dp.include_router(program_router)
    dp.include_router(fallback_router)

    return bot, dp, session_factory


async def _run(user_id: int, keep: bool) -> int:
    bot, dp, session_factory = await _build_dispatcher()
    try:
        await _cleanup_user(session_factory, user_id)

        update = _make_message_update("/start", user_id, msg_id=1)
        await dp.feed_update(bot, update)

        msgs = bot.captured_methods()
        if not msgs:
            print(
                f"FAIL: bot did not reply to /start (user={user_id})",
                file=sys.stderr,
            )
            return 1

        sends = [m for m in msgs if isinstance(m, SendMessage)]
        for i, m in enumerate(sends):
            snippet = (m.text or "").replace("\n", " ")[:80]
            print(f"  msg[{i}] -> {snippet}")

        print(
            f"PASS: bot replied with {len(sends)} message(s) "
            f"({len(msgs)} total methods) to /start (user={user_id})"
        )
        return 0
    except Exception as exc:
        print(
            f"FAIL: {type(exc).__name__}: {exc} (user={user_id})",
            file=sys.stderr,
        )
        traceback.print_exc(file=sys.stderr)
        return 1
    finally:
        if not keep:
            try:
                await _cleanup_user(session_factory, user_id)
            except Exception as exc:
                print(
                    f"warning: cleanup failed: {type(exc).__name__}: {exc}",
                    file=sys.stderr,
                )
        await bot.session.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Bot production smoke test")
    parser.add_argument(
        "--user-id",
        type=int,
        default=None,
        help=(
            "Fake telegram_user_id to send /start from. "
            f"Default: random in {SMOKE_USER_ID_RANGE}."
        ),
    )
    parser.add_argument(
        "--keep",
        action="store_true",
        help="Skip post-run cleanup (leaves smoke user in DB for inspection).",
    )
    args = parser.parse_args()
    user_id = _pick_user_id(args.user_id)
    return asyncio.run(_run(user_id=user_id, keep=args.keep))


if __name__ == "__main__":
    sys.exit(main())
