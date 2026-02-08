import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.admin import router as admin_router
from app.api.auth import router as auth_router
from app.api.events import router as events_router
from app.api.experts import router as experts_router
from app.api.guests import router as guests_router
from app.api.leads import router as leads_router
from app.api.monitoring import router as monitoring_router
from app.api.participation import router as participation_router
from app.api.projects import router as projects_router
from app.api.reminders import router as reminders_router
from app.api.schedule import router as schedule_router
from app.api.users import router as users_router
from app.lifespan import lifespan

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
)

app = FastAPI(
    title="DemoDay AI Navigator",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "https://evt-ai.ru",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(admin_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")
app.include_router(events_router, prefix="/api/v1")
app.include_router(projects_router, prefix="/api/v1")
app.include_router(experts_router, prefix="/api/v1")
app.include_router(schedule_router, prefix="/api/v1")
app.include_router(guests_router, prefix="/api/v1")
app.include_router(participation_router, prefix="/api/v1")
app.include_router(reminders_router, prefix="/api/v1")
app.include_router(leads_router, prefix="/api/v1")
app.include_router(monitoring_router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok"}
