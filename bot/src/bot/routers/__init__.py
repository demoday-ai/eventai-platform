from src.bot.routers.global_cmds import router as global_cmds_router
from src.bot.routers.start import router as start_router
from src.bot.routers.profiling import router as profiling_router
from src.bot.routers.program import router as program_router
from src.bot.routers.detail import router as detail_router
from src.bot.routers.support import router as support_router
from src.bot.routers.expert import router as expert_router
from src.bot.routers.fallback import router as fallback_router

__all__ = [
    "global_cmds_router",
    "start_router",
    "profiling_router",
    "program_router",
    "detail_router",
    "support_router",
    "expert_router",
    "fallback_router",
]
