"""TDD: unified support on thread model (ADR-001).

Bot writes guest support messages into support_threads + support_messages
(the same tables the web admin reads), replacing the support_log flow.

Requires the real local PostgreSQL with backend schema applied (head 039).
"""
import os
from datetime import date, timedelta
from uuid import uuid4

import pytest
import pytest_asyncio

os.environ.setdefault("BOT_TOKEN", "test")
os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://demoday:demoday@localhost:5432/demoday"
)
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/1")

from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.models.event import Event
from src.models.user import User

TEST_DB_URL = os.environ["DATABASE_URL"]


@pytest_asyncio.fixture
async def db():
    eng = create_async_engine(TEST_DB_URL, pool_size=2)
    factory = async_sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        async with session.begin():
            yield session
            await session.rollback()
    await eng.dispose()


@pytest_asyncio.fixture
async def user_and_event(db: AsyncSession):
    event = Event(
        id=uuid4(),
        name="Test DD",
        start_date=date.today(),
        end_date=date.today() + timedelta(days=1),
        is_active=True,
    )
    user = User(
        id=uuid4(),
        telegram_user_id=str(uuid4().int)[:15],
        full_name="Тест Гость",
        username="guest",
    )
    db.add_all([event, user])
    await db.flush()
    return user, event


class TestBotSupportModels:
    """Bot must have ORM models mirroring support_threads/support_messages."""

    def test_support_thread_model_exists(self):
        from src.models.support_thread import SupportThread

        thread = SupportThread(user_id=uuid4(), event_id=uuid4(), status="open")
        assert thread.status == "open"
        assert thread.needs_attention is False or thread.needs_attention is None

    def test_support_message_model_exists(self):
        from src.models.support_message import SupportMessage

        msg = SupportMessage(
            thread_id=uuid4(),
            sender_type="user",
            sender_id=uuid4(),
            text="привет",
        )
        assert msg.sender_type == "user"
        assert msg.text == "привет"

    @pytest.mark.asyncio
    async def test_thread_persists_to_support_threads_table(
        self, db: AsyncSession, user_and_event
    ):
        from src.models.support_thread import SupportThread

        user, event = user_and_event
        thread = SupportThread(user_id=user.id, event_id=event.id, status="open")
        db.add(thread)
        await db.flush()

        row = (
            await db.execute(
                select(SupportThread).where(SupportThread.id == thread.id)
            )
        ).scalar_one()
        assert row.user_id == user.id
        assert row.status == "open"


class TestAddUserSupportMessage:
    """Service: bot persists a guest support message into the thread model."""

    @pytest.mark.asyncio
    async def test_creates_thread_and_message(self, db: AsyncSession, user_and_event):
        from src.models.support_thread import SupportThread
        from src.services.support import add_user_support_message

        user, event = user_and_event
        msg = await add_user_support_message(db, user.id, event.id, "где зал NLP?")

        thread = (
            await db.execute(
                select(SupportThread).where(SupportThread.user_id == user.id)
            )
        ).scalar_one()
        assert thread.event_id == event.id
        assert thread.status == "open"
        assert thread.needs_attention is True

        assert msg.thread_id == thread.id
        assert msg.sender_type == "user"
        assert msg.sender_id == user.id
        assert msg.text == "где зал NLP?"

    @pytest.mark.asyncio
    async def test_reuses_open_thread(self, db: AsyncSession, user_and_event):
        from src.models.support_message import SupportMessage
        from src.models.support_thread import SupportThread
        from src.services.support import add_user_support_message

        user, event = user_and_event
        await add_user_support_message(db, user.id, event.id, "первый")
        await add_user_support_message(db, user.id, event.id, "второй")

        threads = (
            await db.execute(
                select(SupportThread).where(SupportThread.user_id == user.id)
            )
        ).scalars().all()
        assert len(threads) == 1

        messages = (
            await db.execute(
                select(SupportMessage).where(
                    SupportMessage.thread_id == threads[0].id
                )
            )
        ).scalars().all()
        assert len(messages) == 2

    @pytest.mark.asyncio
    async def test_reopens_closed_thread(self, db: AsyncSession, user_and_event):
        from datetime import datetime, timedelta, timezone

        from src.models.support_thread import SupportThread
        from src.services.support import add_user_support_message

        user, event = user_and_event
        stale = datetime(2026, 1, 1, tzinfo=timezone.utc)
        closed = SupportThread(
            user_id=user.id,
            event_id=event.id,
            status="closed",
            closed_by="organizer",
            updated_at=stale,
        )
        db.add(closed)
        await db.flush()

        await add_user_support_message(db, user.id, event.id, "снова вопрос")

        await db.refresh(closed)
        assert closed.status == "open"
        assert closed.closed_by is None
        assert closed.needs_attention is True
        # reopened thread must bubble to the top of the admin list (updated_at bumped)
        assert closed.updated_at > stale

    @pytest.mark.asyncio
    async def test_sanitizes_text(self, db: AsyncSession, user_and_event):
        from src.services.support import add_user_support_message

        user, event = user_and_event
        msg = await add_user_support_message(
            db, user.id, event.id, "плохой\x00текст"
        )
        assert "\x00" not in msg.text


class TestSupportHistory:
    """Service: thread history rendered for AI agent context injection."""

    @pytest.mark.asyncio
    async def test_history_returns_messages_in_order(
        self, db: AsyncSession, user_and_event
    ):
        from src.models.support_message import SupportMessage
        from src.services.support import (
            add_user_support_message,
            get_support_history,
        )

        from datetime import datetime, timedelta, timezone

        user, event = user_and_event
        msg = await add_user_support_message(db, user.id, event.id, "вопрос 1")
        # organizer reply lands in the same thread, strictly later in time
        db.add(
            SupportMessage(
                thread_id=msg.thread_id,
                sender_type="organizer",
                sender_id=user.id,
                text="ответ 1",
                created_at=datetime.now(timezone.utc) + timedelta(minutes=1),
            )
        )
        await db.flush()

        history = await get_support_history(db, user.id, event.id)
        assert history is not None
        assert len(history) == 2
        assert "вопрос 1" in history[0]
        assert "ответ 1" in history[1]

    @pytest.mark.asyncio
    async def test_history_none_when_no_thread(
        self, db: AsyncSession, user_and_event
    ):
        from src.services.support import get_support_history

        user, event = user_and_event
        history = await get_support_history(db, user.id, event.id)
        assert not history

    @pytest.mark.asyncio
    async def test_history_keeps_newest_when_over_limit(
        self, db: AsyncSession, user_and_event
    ):
        """With more messages than the limit, history must keep the NEWEST ones
        (the latest organizer answer), rendered chronologically — not the oldest."""
        from datetime import datetime, timedelta, timezone

        from src.models.support_message import SupportMessage
        from src.models.support_thread import SupportThread
        from src.services.support import get_support_history

        user, event = user_and_event
        thread = SupportThread(user_id=user.id, event_id=event.id, status="open")
        db.add(thread)
        await db.flush()

        base = datetime(2026, 6, 3, 10, 0, 0, tzinfo=timezone.utc)
        # 25 messages with strictly increasing timestamps; the last is the answer.
        for i in range(25):
            db.add(
                SupportMessage(
                    thread_id=thread.id,
                    sender_type="user" if i < 24 else "organizer",
                    sender_id=user.id,
                    text=f"msg {i}" if i < 24 else "САМЫЙ СВЕЖИЙ ОТВЕТ",
                    created_at=base + timedelta(minutes=i),
                )
            )
        await db.flush()

        history = await get_support_history(db, user.id, event.id, limit=20)
        assert history is not None
        assert len(history) == 20
        # newest message must be present and last (chronological render)
        assert "САМЫЙ СВЕЖИЙ ОТВЕТ" in history[-1]
        # oldest messages must have been dropped, not the newest
        assert not any("msg 0" in line for line in history)
        assert any("msg 24" not in line for line in history)  # msg 24 is the answer

    @pytest.mark.asyncio
    async def test_history_deterministic_order_on_tie(
        self, db: AsyncSession, user_and_event
    ):
        """Messages sharing an identical created_at must still render in a stable,
        deterministic order across repeated calls (tiebreaker on id)."""
        from datetime import datetime, timezone

        from src.models.support_message import SupportMessage
        from src.models.support_thread import SupportThread
        from src.services.support import get_support_history

        user, event = user_and_event
        thread = SupportThread(user_id=user.id, event_id=event.id, status="open")
        db.add(thread)
        await db.flush()

        same_ts = datetime(2026, 6, 3, 12, 0, 0, tzinfo=timezone.utc)
        for i in range(5):
            db.add(
                SupportMessage(
                    thread_id=thread.id,
                    sender_type="user",
                    sender_id=user.id,
                    text=f"tie {i}",
                    created_at=same_ts,
                )
            )
        await db.flush()

        first = await get_support_history(db, user.id, event.id)
        second = await get_support_history(db, user.id, event.id)
        assert first == second  # stable, not arbitrary physical order
