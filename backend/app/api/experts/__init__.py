"""Experts API package — collects sub-routers into a single router."""

from fastapi import APIRouter

from app.api.experts.coverage import router as coverage_router
from app.api.experts.crud import router as crud_router
from app.api.experts.escalations import router as escalations_router
from app.api.experts.invites import router as invites_router
from app.api.experts.matching import router as matching_router

router = APIRouter(tags=["experts"])

router.include_router(crud_router)
router.include_router(matching_router)
router.include_router(invites_router)
router.include_router(coverage_router)
router.include_router(escalations_router)
