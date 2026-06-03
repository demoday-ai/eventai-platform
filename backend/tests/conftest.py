import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.models.audit_log import AdminAuditLog
from app.models.base import Base
from app.models.chat_message import ChatMessage
from app.models.clustering_run import ClusteringRun
from app.models.event import Event
from app.models.notification import Notification
from app.models.organizer import Organizer
from app.models.project import Project
from app.models.project_tag import ProjectTag
from app.models.role import Role
from app.models.room import Room
from app.models.room_project import RoomProject
from app.models.schedule_change_log import ScheduleChangeLog
from app.models.schedule_slot import ScheduleSlot
from app.models.support_message import SupportMessage
from app.models.support_thread import SupportThread
from app.models.tag import Tag
from app.models.user import User
from app.models.user_role import UserRole


@pytest.fixture(scope="session")
async def async_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(
            Base.metadata.create_all,
            tables=[
                Event.__table__,
                Project.__table__,
                Tag.__table__,
                ProjectTag.__table__,
                ClusteringRun.__table__,
                Room.__table__,
                RoomProject.__table__,
                User.__table__,
                AdminAuditLog.__table__,
                Organizer.__table__,
                ScheduleSlot.__table__,
                ScheduleChangeLog.__table__,
                Notification.__table__,
                SupportThread.__table__,
                SupportMessage.__table__,
                ChatMessage.__table__,
                Role.__table__,
                UserRole.__table__,
            ],
        )
    yield engine
    await engine.dispose()


@pytest.fixture
async def session(async_engine):
    async_session = sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
        await session.rollback()
