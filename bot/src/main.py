"""EventAI Agent - main entry point.

Initializes:
- Redis connection (FSM storage + throttle)
- PlatformClient (LLM proxy) with registration
- aiogram Bot + Dispatcher
- FSM storage (Redis-backed)
- All middlewares (DB session, platform, throttle, reconcile)
- All routers (start, profiling, program, detail, support, expert)
- Health check endpoint (aiohttp on port 8080)
- Polling loop
- Graceful shutdown on SIGTERM
"""

import asyncio
import logging
import signal

import redis.asyncio as aioredis
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.redis import RedisStorage

from src.bot.middlewares import (
    DbSessionMiddleware,
    PlatformMiddleware,
    ReconcileMiddleware,
    ThrottleMiddleware,
)
from src.bot.routers import (
    detail_router,
    expert_router,
    fallback_router,
    global_cmds_router,
    profiling_router,
    program_router,
    start_router,
    support_router,
)
from src.core.config import settings
from src.services.platform_client import PlatformClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def health_handler(request: web.Request) -> web.Response:
    """Health check endpoint for container orchestration."""
    return web.Response(text="ok")


async def run_health_server() -> web.AppRunner:
    """Start aiohttp health check server on port 8080."""
    app = web.Application()
    app.router.add_get("/health", health_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()
    logger.info("Health endpoint listening on :8080/health")
    return runner


async def main() -> None:
    logger.info("EventAI Agent starting...")

    # --- Redis ---
    redis_kwargs = {"decode_responses": True}
    if settings.redis_password:
        redis_kwargs["password"] = settings.redis_password
    redis = aioredis.from_url(settings.redis_url, **redis_kwargs)
    try:
        await redis.ping()
        logger.info("Redis connected: %s", settings.redis_url)
    except Exception as e:
        logger.error("Redis connection failed: %s", e)
        raise

    # --- Platform Client ---
    # Standalone mode: use OpenRouter directly (no llm-agent-platform)
    # Platform mode: register with llm-agent-platform proxy
    if settings.openrouter_api_key and not settings.master_token:
        from pydantic import SecretStr
        platform = PlatformClient(
            platform_url="https://openrouter.ai/api",
            master_token="unused",
        )
        platform._token = SecretStr(settings.openrouter_api_key)
        logger.info("Standalone mode: OpenRouter direct (%s)", settings.llm_model)
    else:
        platform = PlatformClient(
            platform_url=settings.platform_url,
            master_token=settings.master_token,
        )
        try:
            await platform.register()
            logger.info("Platform registered: %s", platform)
        except Exception as e:
            logger.warning("Platform registration failed (will retry): %s", e)

    # --- Auto-seed: skipped in monorepo mode.
    #     - Schema is managed by Alembic in backend/.
    #     - Embedding/artifact parsing run via `python -m scripts.parse_artifacts` CLI.

    # --- FSM Storage ---
    # Use a separate Redis connection for FSM (needs decode_responses=True)
    storage = RedisStorage(redis)

    # --- Bot + Dispatcher ---
    if not settings.bot_token or settings.bot_token == "test":
        logger.error(
            "BOT_TOKEN is not set or invalid. "
            "Get a token from @BotFather in Telegram and set it in .env"
        )
        raise SystemExit(1)

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=None),
    )
    dp = Dispatcher(storage=storage)

    # --- Middlewares ---
    # Order matters: throttle -> db -> platform -> reconcile
    # Applied to both message and callback_query updates.
    dp.message.middleware(ThrottleMiddleware(redis=redis, rate_limit=settings.rate_limit_per_minute))
    dp.callback_query.middleware(ThrottleMiddleware(redis=redis, rate_limit=settings.rate_limit_per_minute))

    dp.message.middleware(DbSessionMiddleware())
    dp.callback_query.middleware(DbSessionMiddleware())

    dp.message.middleware(PlatformMiddleware(platform=platform))
    dp.callback_query.middleware(PlatformMiddleware(platform=platform))

    dp.message.middleware(ReconcileMiddleware())
    dp.callback_query.middleware(ReconcileMiddleware())

    # --- Routers ---
    # Registration order matters: more specific routers first.
    # global_cmds_router goes FIRST so /reset, /profile, /rebuild, /support, /help
    #   work in any FSM state (otherwise state-routers' F.text catch-all swallows
    #   the command as profile text).
    # start_router handles /start (CommandStart filter).
    # profiling handles onboard_nl_profile + onboard_confirm states.
    # expert handles expert_dashboard + expert_evaluation states.
    # detail handles view_detail state.
    # support handles support_chat state.
    # program handles view_program state (broadest text handler).
    # fallback_router MUST be last: catch-all for messages without state and
    #   stale callbacks.
    dp.include_router(global_cmds_router)
    dp.include_router(start_router)
    dp.include_router(profiling_router)
    dp.include_router(expert_router)
    dp.include_router(detail_router)
    dp.include_router(support_router)
    dp.include_router(program_router)
    dp.include_router(fallback_router)

    # --- Health endpoint ---
    health_runner = await run_health_server()

    # --- Graceful shutdown ---
    shutdown_event = asyncio.Event()

    def signal_handler() -> None:
        logger.info("Received shutdown signal")
        shutdown_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, signal_handler)

    # --- Start polling ---
    logger.info("Starting polling...")
    polling_task = asyncio.create_task(
        dp.start_polling(bot, handle_signals=False)
    )

    # Wait for shutdown signal
    await shutdown_event.wait()

    logger.info("Shutting down...")

    # Stop polling
    await dp.stop_polling()
    polling_task.cancel()
    try:
        await polling_task
    except asyncio.CancelledError:
        pass

    # Cleanup
    await health_runner.cleanup()
    await platform.close()
    await redis.aclose()
    await bot.session.close()

    logger.info("EventAI Agent stopped.")


if __name__ == "__main__":
    asyncio.run(main())
