"""Admin API package — collects sub-routers into a single router."""

from fastapi import APIRouter

from app.api.admin.audit import router as audit_router
from app.api.admin.briefing import router as briefing_router
from app.api.admin.clustering import router as clustering_router
from app.api.admin.dashboard import router as dashboard_router
from app.api.admin.events import router as events_router
from app.api.admin.guests import router as guests_router
from app.api.admin.llm_config import router as llm_config_router
from app.api.admin.messaging import router as messaging_router
from app.api.admin.organizers import router as organizers_router
from app.api.admin.projects import router as projects_router
from app.api.admin.rooms import router as rooms_router
from app.api.admin.tags import router as tags_router

router = APIRouter(prefix="/admin", tags=["Admin"])

router.include_router(dashboard_router)
router.include_router(rooms_router)
router.include_router(tags_router)
router.include_router(events_router)
router.include_router(guests_router)
router.include_router(projects_router)
router.include_router(briefing_router)
router.include_router(messaging_router)
router.include_router(audit_router)
router.include_router(organizers_router)
router.include_router(llm_config_router)
router.include_router(clustering_router)
