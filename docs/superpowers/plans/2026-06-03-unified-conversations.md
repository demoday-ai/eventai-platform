# Unified Conversations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Organizer sees the full guest↔bot conversation, can browse all chats, write into any chat (auto-takeover that mutes the AI), and release control back to the AI which retains the organizer dialogue in its context.

**Architecture:** `chat_messages` is the single source of truth for all messages (roles `user`/`assistant`/`organizer`). `support_threads` is a per-(user,event) metadata overlay carrying `needs_attention`, `status`, and a new `taken_over` flag. The admin works by `user_id`; API renamed `/admin/support/*` → `/admin/conversations/*`. `support_messages` is deprecated (no longer written).

**Tech Stack:** FastAPI + SQLAlchemy 2.0 async (backend, sqlite tests), aiogram 3 + PydanticAI (bot, real-Postgres tests at `bot_test`), React 19 + Vitest (frontend).

**Test DB note (bot):** bot router/service tests run against a real Postgres DB `bot_test` created from `src.models.Base.metadata.create_all`. After adding a column to a bot model, recreate it:
```bash
docker exec demoday-core-db-1 psql -U demoday -d demoday -c "DROP DATABASE IF EXISTS bot_test;"
docker exec demoday-core-db-1 psql -U demoday -d demoday -c "CREATE DATABASE bot_test;"
docker exec demoday-core-db-1 psql -U demoday -d bot_test -c "CREATE EXTENSION IF NOT EXISTS vector;"
cd bot && PYTHONPATH="$PWD" BOT_TOKEN=test DATABASE_URL="postgresql+asyncpg://demoday:demoday@localhost:5432/bot_test" REDIS_URL="redis://localhost:6379/1" python3.12 -c "import asyncio; from sqlalchemy.ext.asyncio import create_async_engine; from src.models import Base;\
import asyncio as a;\
"  # use the inline script from prior sessions
```
Bot test env prefix (use for every bot pytest run):
`PYTHONPATH="$PWD" BOT_TOKEN=test DATABASE_URL="postgresql+asyncpg://demoday:demoday@localhost:5432/bot_test" REDIS_URL="redis://localhost:6379/1"`

---

## Phase 1 — Migration + ORM `taken_over`

### Task 1: Add `taken_over` column (migration + both ORM models)

**Files:**
- Create: `backend/alembic/versions/041_conversation_takeover.py`
- Modify: `backend/app/models/support_thread.py`
- Modify: `bot/src/models/support_thread.py`
- Test: `backend/tests/test_support_chat.py`

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/test_support_chat.py` inside `class TestSupportThreadModel`:

```python
    def test_thread_has_taken_over_default_false(self):
        from app.models.support_thread import SupportThread

        thread = SupportThread(user_id=uuid.uuid4(), event_id=uuid.uuid4())
        assert thread.taken_over is False or thread.taken_over is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python3.12 -m pytest tests/test_support_chat.py -k taken_over -q`
Expected: FAIL — `AttributeError: 'SupportThread' object has no attribute 'taken_over'`

- [ ] **Step 3: Add column to backend model**

In `backend/app/models/support_thread.py`, after the `needs_attention` column:

```python
    taken_over: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
```

- [ ] **Step 4: Add column to bot mirror model**

In `bot/src/models/support_thread.py`, after the `needs_attention` column:

```python
    taken_over: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )
```

- [ ] **Step 5: Write the migration**

Create `backend/alembic/versions/041_conversation_takeover.py`:

```python
"""Add taken_over flag to support_threads (conversation takeover).

Revision ID: 041_conversation_takeover
Revises: 040_*  # set to actual current head if different from 039
Create Date: 2026-06-03

When an organizer replies from the admin, the conversation is "taken over":
the AI agent stops auto-replying in that chat until released.
"""

from alembic import op
import sqlalchemy as sa

revision = "041_conversation_takeover"
down_revision = "039_event_bot_cols"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "support_threads",
        sa.Column("taken_over", sa.Boolean(), nullable=False, server_default="false"),
    )


def downgrade() -> None:
    op.drop_column("support_threads", "taken_over")
```

NOTE: confirm `down_revision` matches `alembic heads` (currently `039_event_bot_cols`).

- [ ] **Step 6: Run backend test to verify pass + recreate bot_test DB**

Run: `cd backend && python3.12 -m pytest tests/test_support_chat.py -k taken_over -q`
Expected: PASS

Recreate `bot_test` (see Test DB note) so the bot column exists for later phases.

- [ ] **Step 7: Commit**

```bash
git add backend/alembic/versions/041_conversation_takeover.py backend/app/models/support_thread.py bot/src/models/support_thread.py backend/tests/test_support_chat.py
git commit -m "feat(conversations): taken_over flag on support_threads"
```

---

## Phase 2 — Backend conversation service + API

### Task 2: `conversation_service.get_conversations` (list from chat_messages)

**Files:**
- Create: `backend/app/services/admin/conversation_service.py`
- Test: `backend/tests/test_conversations.py`
- Modify: `backend/tests/conftest.py` (add ChatMessage to create_all)

- [ ] **Step 1: Add ChatMessage table to test engine**

In `backend/tests/conftest.py`, import and add to the `tables=[...]` list:

```python
from app.models.chat_message import ChatMessage
```
and add `ChatMessage.__table__,` to the `tables=[...]` list.

- [ ] **Step 2: Write the failing test**

Create `backend/tests/test_conversations.py`:

```python
"""Tests for unified conversations (chat_messages + thread metadata)."""
from datetime import date, datetime, timedelta, timezone

import pytest

from app.models.chat_message import ChatMessage
from app.models.event import Event
from app.models.support_thread import SupportThread
from app.models.user import User
from app.services.admin import conversation_service


async def _seed_user_event(session):
    event = Event(name="DD", start_date=date.today(), end_date=date.today())
    user = User(telegram_user_id="g1", full_name="Guest One")
    session.add_all([event, user])
    await session.flush()
    return user, event


class TestGetConversations:
    @pytest.mark.asyncio
    async def test_lists_guest_with_only_chat_messages(self, session):
        """A guest who only chatted with the AI (no /support) still appears."""
        user, event = await _seed_user_event(session)
        base = datetime(2026, 6, 3, 10, 0, tzinfo=timezone.utc)
        session.add_all([
            ChatMessage(user_id=user.id, event_id=event.id, role="user",
                        content="привет", created_at=base),
            ChatMessage(user_id=user.id, event_id=event.id, role="assistant",
                        content="здравствуйте", created_at=base + timedelta(minutes=1)),
        ])
        await session.flush()

        result = await conversation_service.get_conversations(session, event.id, filter="all")
        assert result.total == 1
        conv = result.conversations[0]
        assert conv.user_id == str(user.id)
        assert conv.user_name == "Guest One"
        assert conv.message_count == 2
        assert conv.last_message == "здравствуйте"
        assert conv.needs_attention is False
        assert conv.taken_over is False
        assert conv.unread is False  # last message is assistant

    @pytest.mark.asyncio
    async def test_unread_true_when_last_is_user(self, session):
        user, event = await _seed_user_event(session)
        base = datetime(2026, 6, 3, 10, 0, tzinfo=timezone.utc)
        session.add(ChatMessage(user_id=user.id, event_id=event.id, role="user",
                                content="вопрос", created_at=base))
        await session.flush()
        result = await conversation_service.get_conversations(session, event.id, filter="all")
        assert result.conversations[0].unread is True

    @pytest.mark.asyncio
    async def test_filter_attention(self, session):
        user, event = await _seed_user_event(session)
        base = datetime(2026, 6, 3, 10, 0, tzinfo=timezone.utc)
        session.add(ChatMessage(user_id=user.id, event_id=event.id, role="user",
                                content="x", created_at=base))
        session.add(SupportThread(user_id=user.id, event_id=event.id,
                                  status="open", needs_attention=True))
        await session.flush()
        attn = await conversation_service.get_conversations(session, event.id, filter="attention")
        assert attn.total == 1
        # a guest without needs_attention is excluded
        u2 = User(telegram_user_id="g2", full_name="Guest Two")
        session.add(u2)
        await session.flush()
        session.add(ChatMessage(user_id=u2.id, event_id=event.id, role="user",
                                content="y", created_at=base))
        await session.flush()
        attn2 = await conversation_service.get_conversations(session, event.id, filter="attention")
        assert attn2.total == 1
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd backend && python3.12 -m pytest tests/test_conversations.py -q`
Expected: FAIL — `ModuleNotFoundError: app.services.admin.conversation_service`

- [ ] **Step 4: Write the service + schemas**

Add to `backend/app/schemas/support.py` (kept file, new schemas):

```python
class ConversationResponse(BaseModel):
    user_id: str
    user_name: str
    user_username: str | None = None
    user_role: str | None = None
    last_message: str | None = None
    last_message_at: str | None = None
    message_count: int = 0
    unread: bool = False
    needs_attention: bool = False
    taken_over: bool = False
    status: str = "open"


class ConversationListResponse(BaseModel):
    conversations: list[ConversationResponse]
    total: int


class ConversationMessageResponse(BaseModel):
    id: str
    role: str  # "user" | "assistant" | "organizer"
    content: str
    created_at: str
```

Create `backend/app/services/admin/conversation_service.py`:

```python
"""Unified conversation service: messages from chat_messages, state from support_threads."""
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat_message import ChatMessage
from app.models.role import Role
from app.models.support_thread import SupportThread
from app.models.user import User
from app.models.user_role import UserRole
from app.schemas.support import (
    ConversationListResponse,
    ConversationMessageResponse,
    ConversationResponse,
)


async def get_conversations(
    session: AsyncSession,
    event_id: UUID,
    filter: str = "all",
    role: str | None = None,
) -> ConversationListResponse:
    """List conversations: every user with chat_messages in the event,
    plus support_threads metadata. filter in {all, attention, taken_over}."""
    # Distinct users that have chat history in this event
    user_ids_subq = (
        select(ChatMessage.user_id)
        .where(ChatMessage.event_id == event_id)
        .distinct()
        .subquery()
    )
    users = (
        await session.execute(
            select(User).where(User.id.in_(select(user_ids_subq.c.user_id)))
        )
    ).scalars().all()
    if not users:
        return ConversationListResponse(conversations=[], total=0)

    uids = [u.id for u in users]

    # message counts
    counts = dict(
        (
            await session.execute(
                select(ChatMessage.user_id, func.count(ChatMessage.id))
                .where(ChatMessage.event_id == event_id, ChatMessage.user_id.in_(uids))
                .group_by(ChatMessage.user_id)
            )
        ).all()
    )

    # last message per user (DISTINCT ON)
    last_rows = (
        await session.execute(
            select(ChatMessage)
            .where(ChatMessage.event_id == event_id, ChatMessage.user_id.in_(uids))
            .order_by(ChatMessage.user_id, ChatMessage.created_at.desc(), ChatMessage.id.desc())
            .distinct(ChatMessage.user_id)
        )
    ).scalars().all()
    last_by_user = {m.user_id: m for m in last_rows}

    # threads
    threads = (
        await session.execute(
            select(SupportThread).where(
                SupportThread.event_id == event_id, SupportThread.user_id.in_(uids)
            )
        )
    ).scalars().all()
    thread_by_user = {t.user_id: t for t in threads}

    # roles
    role_rows = (
        await session.execute(
            select(UserRole.user_id, Role.code)
            .join(Role)
            .where(UserRole.user_id.in_(uids), UserRole.event_id == event_id)
        )
    ).all()
    role_by_user = dict(role_rows)

    items: list[ConversationResponse] = []
    for u in users:
        t = thread_by_user.get(u.id)
        last = last_by_user.get(u.id)
        needs_attention = t.needs_attention if t else False
        taken_over = t.taken_over if t else False
        status = t.status if t else "open"
        user_role = role_by_user.get(u.id)

        if filter == "attention" and not needs_attention:
            continue
        if filter == "taken_over" and not taken_over:
            continue
        if role and user_role != role:
            continue

        items.append(
            ConversationResponse(
                user_id=str(u.id),
                user_name=u.full_name or u.username or "N/A",
                user_username=u.username,
                user_role=user_role,
                last_message=last.content[:100] if last else None,
                last_message_at=last.created_at.isoformat() if last else None,
                message_count=counts.get(u.id, 0),
                unread=(last.role == "user") if last else False,
                needs_attention=needs_attention,
                taken_over=taken_over,
                status=status,
            )
        )
    return ConversationListResponse(conversations=items, total=len(items))


async def get_messages(
    session: AsyncSession, user_id: UUID, event_id: UUID
) -> list[ConversationMessageResponse]:
    rows = (
        await session.execute(
            select(ChatMessage)
            .where(ChatMessage.user_id == user_id, ChatMessage.event_id == event_id)
            .order_by(ChatMessage.created_at.asc(), ChatMessage.id.asc())
        )
    ).scalars().all()
    return [
        ConversationMessageResponse(
            id=str(m.id), role=m.role, content=m.content, created_at=m.created_at.isoformat()
        )
        for m in rows
    ]
```

- [ ] **Step 5: Run tests to verify pass**

Run: `cd backend && python3.12 -m pytest tests/test_conversations.py -q`
Expected: PASS (3 tests)

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/admin/conversation_service.py backend/app/schemas/support.py backend/tests/test_conversations.py backend/tests/conftest.py
git commit -m "feat(conversations): backend list+messages from chat_messages"
```

### Task 3: `conversation_service` reply / release / close (+ takeover + delivery)

**Files:**
- Modify: `backend/app/services/admin/conversation_service.py`
- Test: `backend/tests/test_conversations.py`

- [ ] **Step 1: Write the failing tests**

Add to `backend/tests/test_conversations.py`:

```python
class TestReplyReleaseClose:
    @pytest.mark.asyncio
    async def test_reply_writes_organizer_message_and_takes_over(self, session):
        user, event = await _seed_user_event(session)
        organizer = User(telegram_user_id="org", full_name="Org")
        session.add(organizer)
        await session.flush()

        msg = await conversation_service.post_organizer_message(
            session, user.id, event.id, organizer.id, "ответ орга"
        )
        assert msg.role == "organizer"
        assert msg.content == "ответ орга"

        thread = (await session.execute(
            select(SupportThread).where(SupportThread.user_id == user.id)
        )).scalar_one()
        assert thread.taken_over is True
        assert thread.needs_attention is False

        # message persisted in chat_messages
        rows = await conversation_service.get_messages(session, user.id, event.id)
        assert any(r.role == "organizer" and r.content == "ответ орга" for r in rows)

    @pytest.mark.asyncio
    async def test_release_clears_taken_over(self, session):
        user, event = await _seed_user_event(session)
        org = User(telegram_user_id="org2", full_name="Org2")
        session.add(org)
        await session.flush()
        await conversation_service.post_organizer_message(session, user.id, event.id, org.id, "x")
        await conversation_service.release(session, user.id, event.id)
        thread = (await session.execute(
            select(SupportThread).where(SupportThread.user_id == user.id)
        )).scalar_one()
        assert thread.taken_over is False

    @pytest.mark.asyncio
    async def test_close_sets_closed_and_clears_takeover(self, session):
        user, event = await _seed_user_event(session)
        org = User(telegram_user_id="org3", full_name="Org3")
        session.add(org)
        await session.flush()
        await conversation_service.post_organizer_message(session, user.id, event.id, org.id, "x")
        await conversation_service.close(session, user.id, event.id)
        thread = (await session.execute(
            select(SupportThread).where(SupportThread.user_id == user.id)
        )).scalar_one()
        assert thread.status == "closed"
        assert thread.taken_over is False
```

- [ ] **Step 2: Run to verify fail**

Run: `cd backend && python3.12 -m pytest tests/test_conversations.py::TestReplyReleaseClose -q`
Expected: FAIL — `AttributeError: module ... has no attribute 'post_organizer_message'`

- [ ] **Step 3: Implement service functions**

Append to `backend/app/services/admin/conversation_service.py`:

```python
from datetime import datetime, timezone

from app.models.chat_message import ChatMessage as _ChatMessage  # already imported above; keep single import


async def _get_or_create_thread(
    session: AsyncSession, user_id: UUID, event_id: UUID
) -> SupportThread:
    thread = (
        await session.execute(
            select(SupportThread)
            .where(SupportThread.user_id == user_id, SupportThread.event_id == event_id)
            .order_by(SupportThread.created_at.desc())
            .limit(1)
            .with_for_update(skip_locked=False)
        )
    ).scalar_one_or_none()
    if thread:
        return thread
    thread = SupportThread(user_id=user_id, event_id=event_id, status="open")
    session.add(thread)
    await session.flush()
    return thread


async def post_organizer_message(
    session: AsyncSession,
    user_id: UUID,
    event_id: UUID,
    organizer_id: UUID,
    text: str,
) -> ConversationMessageResponse:
    """Persist an organizer message into chat_messages, take over the chat."""
    msg = ChatMessage(
        user_id=user_id, event_id=event_id, role="organizer", content=text
    )
    session.add(msg)
    thread = await _get_or_create_thread(session, user_id, event_id)
    thread.taken_over = True
    thread.needs_attention = False
    thread.updated_at = datetime.now(timezone.utc)
    await session.flush()
    await session.refresh(msg)
    return ConversationMessageResponse(
        id=str(msg.id), role=msg.role, content=msg.content,
        created_at=msg.created_at.isoformat(),
    )


async def release(session: AsyncSession, user_id: UUID, event_id: UUID) -> None:
    thread = await _get_or_create_thread(session, user_id, event_id)
    thread.taken_over = False
    thread.updated_at = datetime.now(timezone.utc)
    await session.flush()


async def close(session: AsyncSession, user_id: UUID, event_id: UUID) -> None:
    thread = await _get_or_create_thread(session, user_id, event_id)
    thread.status = "closed"
    thread.taken_over = False
    thread.updated_at = datetime.now(timezone.utc)
    await session.flush()
```

NOTE: remove the duplicate `_ChatMessage` import line — `ChatMessage` and `datetime` should be imported once at the top of the file. Consolidate imports.

- [ ] **Step 4: Run tests**

Run: `cd backend && python3.12 -m pytest tests/test_conversations.py -q`
Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/admin/conversation_service.py backend/tests/test_conversations.py
git commit -m "feat(conversations): organizer reply/release/close with takeover"
```

### Task 4: API router `/admin/conversations/*` + Telegram delivery

**Files:**
- Create: `backend/app/api/admin/conversations.py`
- Modify: `backend/app/api/admin/__init__.py`
- Delete: `backend/app/api/admin/support.py` (replaced)
- Test: `backend/tests/test_conversations.py`

- [ ] **Step 1: Write the failing API test**

Add to `backend/tests/test_conversations.py` (uses FastAPI app + override; follow the pattern already used in other `backend/tests/test_admin_*.py` files — read one to match the client fixture). Minimal endpoint smoke:

```python
class TestConversationAPI:
    @pytest.mark.asyncio
    async def test_list_endpoint_returns_200(self, client):
        resp = await client.get("/api/v1/admin/conversations?filter=all")
        assert resp.status_code == 200
        assert "conversations" in resp.json()
```

NOTE: confirm the `client` fixture name/shape by reading `backend/tests/test_admin_events.py`. Match its async client usage exactly.

- [ ] **Step 2: Run to verify fail**

Run: `cd backend && python3.12 -m pytest tests/test_conversations.py::TestConversationAPI -q`
Expected: FAIL — 404 (route not mounted)

- [ ] **Step 3: Write the router**

Create `backend/app/api/admin/conversations.py` (delivery mirrors old support.py:reply_to_thread which used `bot_messenger.get_send_bot()`):

```python
"""Admin conversation endpoints (unified chat_messages view + organizer takeover)."""
import logging
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import check_organizer
from app.database import get_session
from app.models.user import User
from app.schemas.support import (
    ConversationListResponse,
    ConversationMessageResponse,
    SendMessageRequest,
)
from app.services.admin import conversation_service
from app.services.core import user_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/conversations", response_model=ConversationListResponse)
async def list_conversations(
    filter: Literal["all", "attention", "taken_over"] = "all",
    role: str | None = None,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(check_organizer),
):
    event = await user_service.get_current_event(db)
    if not event:
        raise HTTPException(status_code=404, detail="No active event")
    return await conversation_service.get_conversations(db, event.id, filter=filter, role=role)


@router.get("/conversations/{user_id}/messages", response_model=list[ConversationMessageResponse])
async def get_conversation_messages(
    user_id: UUID,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(check_organizer),
):
    event = await user_service.get_current_event(db)
    if not event:
        raise HTTPException(status_code=404, detail="No active event")
    return await conversation_service.get_messages(db, user_id, event.id)


@router.post("/conversations/{user_id}/reply", response_model=ConversationMessageResponse)
async def reply_to_conversation(
    user_id: UUID,
    body: SendMessageRequest,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(check_organizer),
):
    event = await user_service.get_current_event(db)
    if not event:
        raise HTTPException(status_code=404, detail="No active event")
    msg = await conversation_service.post_organizer_message(
        db, user_id, event.id, current_user.id, body.text
    )
    await db.commit()

    target = await db.get(User, user_id)
    if target and target.telegram_user_id:
        try:
            from app.services.core.bot_messenger import get_send_bot

            bot = get_send_bot()
            org_name = current_user.full_name or "Организатор"
            await bot.send_message(
                chat_id=int(target.telegram_user_id),
                text=f"Ответ от организатора ({org_name}):\n\n{body.text}",
            )
        except Exception as e:
            logger.warning("Failed to deliver organizer message via Telegram: %s", e)
    return msg


@router.post("/conversations/{user_id}/release")
async def release_conversation(
    user_id: UUID,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(check_organizer),
):
    event = await user_service.get_current_event(db)
    if not event:
        raise HTTPException(status_code=404, detail="No active event")
    await conversation_service.release(db, user_id, event.id)
    await db.commit()
    return {"status": "released"}


@router.post("/conversations/{user_id}/close")
async def close_conversation(
    user_id: UUID,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(check_organizer),
):
    event = await user_service.get_current_event(db)
    if not event:
        raise HTTPException(status_code=404, detail="No active event")
    await conversation_service.close(db, user_id, event.id)
    await db.commit()
    return {"status": "closed"}
```

- [ ] **Step 4: Mount router, remove old support router**

In `backend/app/api/admin/__init__.py`:
- Replace `from app.api.admin.support import router as support_router` with `from app.api.admin.conversations import router as conversations_router`
- Replace `router.include_router(support_router)` with `router.include_router(conversations_router)`
- Delete file `backend/app/api/admin/support.py`
- Delete obsolete service `backend/app/services/admin/support_service.py` ONLY IF nothing else imports it (grep first). If imported elsewhere, leave it.

- [ ] **Step 5: Run full backend suite**

Run: `cd backend && python3.12 -m pytest tests/ --ignore=tests/test_handlers/test_onboarding.py --ignore=tests/e2e -q`
Expected: PASS. Fix any test that imported the old support router/service.

- [ ] **Step 6: ruff + commit**

```bash
cd backend && python3.12 -m ruff check app/api/admin/conversations.py app/services/admin/conversation_service.py
git add -A backend/app/api/admin backend/app/services/admin backend/tests/test_conversations.py
git commit -m "feat(conversations): /admin/conversations API + delivery, drop support router"
```

---

## Phase 3 — Bot: takeover guard + chat_messages context + /support

### Task 5: Bot helpers — takeover check + organizer-aware history from chat_messages

**Files:**
- Modify: `bot/src/services/support.py`
- Test: `bot/tests/test_support_threads.py`

- [ ] **Step 1: Write the failing tests**

Add to `bot/tests/test_support_threads.py`:

```python
class TestTakeover:
    @pytest.mark.asyncio
    async def test_is_taken_over_false_without_thread(self, db, user_and_event):
        from src.services.support import is_taken_over

        user, event = user_and_event
        assert await is_taken_over(db, user.id, event.id) is False

    @pytest.mark.asyncio
    async def test_is_taken_over_true_when_flag_set(self, db, user_and_event):
        from src.models.support_thread import SupportThread
        from src.services.support import is_taken_over

        user, event = user_and_event
        db.add(SupportThread(user_id=user.id, event_id=event.id, status="open", taken_over=True))
        await db.flush()
        assert await is_taken_over(db, user.id, event.id) is True
```

- [ ] **Step 2: Run to verify fail**

Run (bot env prefix): `cd bot && python3.12 -m pytest tests/test_support_threads.py::TestTakeover -q`
Expected: FAIL — `ImportError: cannot import name 'is_taken_over'`

- [ ] **Step 3: Implement `is_taken_over`**

Add to `bot/src/services/support.py`:

```python
async def is_taken_over(db: AsyncSession, user_id: UUID, event_id: UUID) -> bool:
    """True if an organizer has taken over this conversation (AI must stay silent)."""
    row = (
        await db.execute(
            select(SupportThread.taken_over)
            .where(
                SupportThread.user_id == user_id,
                SupportThread.event_id == event_id,
            )
            .order_by(SupportThread.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    return bool(row)
```

- [ ] **Step 4: Change `add_user_support_message` to write chat_messages**

In `bot/src/services/support.py`, change `add_user_support_message` so the user
message goes to `ChatMessage` (not `SupportMessage`), keeping the thread flag:

```python
from src.models.chat_message import ChatMessage

async def add_user_support_message(
    db: AsyncSession, user_id: UUID, event_id: UUID, text: str
) -> ChatMessage:
    """Persist a guest support message into chat_messages (ADR-001 superseded:
    chat_messages is the single source of truth) and flag the thread."""
    thread = await _get_or_create_open_thread(db, user_id, event_id)
    thread.needs_attention = True
    thread.updated_at = datetime.now(timezone.utc)

    msg = ChatMessage(
        user_id=user_id,
        event_id=event_id,
        role="user",
        content=(sanitize_text(text) or "")[:1000],
    )
    db.add(msg)
    await db.flush()
    await db.refresh(msg)
    return msg
```

- [ ] **Step 5: Update the existing add_user_support_message test**

In `bot/tests/test_support_threads.py`, the existing `TestAddUserSupportMessage`
tests assert on `SupportMessage`. Change them to assert on `ChatMessage`:
replace `from src.models.support_message import SupportMessage` usages with
`from src.models.chat_message import ChatMessage`, query `ChatMessage` where it
queried `SupportMessage`, assert `role == "user"` instead of `sender_type`, and
`content` instead of `text`. Keep the thread `needs_attention`/reopen assertions.

- [ ] **Step 6: Rewrite get_support_history to read chat_messages**

Replace the body of `get_support_history` in `bot/src/services/support.py` to read
from `ChatMessage` (roles user/assistant/organizer), newest-N + reverse:

```python
async def get_support_history(
    db: AsyncSession, user_id: UUID, event_id: UUID, limit: int = 20
) -> list[str] | None:
    """Render recent conversation lines for AI agent context, from chat_messages."""
    messages = (
        await db.execute(
            select(ChatMessage)
            .where(ChatMessage.user_id == user_id, ChatMessage.event_id == event_id)
            .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
            .limit(limit)
        )
    ).scalars().all()
    if not messages:
        return None
    label = {"user": "Пользователь", "assistant": "Ассистент", "organizer": "Организатор"}
    lines: list[str] = []
    for m in reversed(messages):
        lines.append(f"{label.get(m.role, m.role)}: {m.content}")
    return lines
```

Update the `TestSupportHistory` tests in `bot/tests/test_support_threads.py` to
seed `ChatMessage` rows (role/content) instead of `SupportMessage` (sender_type/text),
adjusting the assertions (the newest-N + chronological + tiebreaker behavior is unchanged).

- [ ] **Step 7: Run tests**

Run (bot env prefix): `cd bot && python3.12 -m pytest tests/test_support_threads.py -q`
Expected: PASS (all, including updated existing tests)

- [ ] **Step 8: ruff + commit**

```bash
cd bot && python3.12 -m ruff check src/services/support.py
git add bot/src/services/support.py bot/tests/test_support_threads.py
git commit -m "feat(bot): takeover check + chat_messages-based support write/history"
```

### Task 6: Bot router — mute AI when taken over

**Files:**
- Modify: `bot/src/bot/routers/program.py`
- Test: `bot/tests/test_routers.py`

- [ ] **Step 1: Write the failing test**

Add to `bot/tests/test_routers.py` in `class TestProgramRouter` (follow the seed/_setup_dp pattern of neighbouring tests):

```python
    @pytest.mark.asyncio
    async def test_view_program_skips_agent_when_taken_over(self, db: AsyncSession, seed):
        """If the conversation is taken over, the AI agent must NOT reply."""
        from src.models.chat_message import ChatMessage
        from src.models.support_thread import SupportThread

        uid = 9061
        user = User(telegram_user_id=str(uid), full_name="Taken Over")
        db.add(user)
        await db.flush()
        db.add(SupportThread(user_id=user.id, event_id=seed["event"].id,
                             status="open", taken_over=True))
        await db.flush()

        dp, bot = _setup_dp(db)
        await _set_state(dp, bot, BotStates.view_program.state, user_id=uid)
        await _set_data(dp, bot, {
            "user_id": str(user.id),
            "event_id": str(seed["event"].id),
        }, user_id=uid)
        _queue_send(bot)

        update = make_message("вопрос боту", user_id=uid, chat_id=uid)
        await dp.feed_update(bot, update)

        # user message stored
        rows = (await db.execute(
            select(ChatMessage).where(ChatMessage.user_id == user.id, ChatMessage.role == "user")
        )).scalars().all()
        assert len(rows) == 1
        # NO assistant reply was written
        assistant = (await db.execute(
            select(ChatMessage).where(ChatMessage.user_id == user.id, ChatMessage.role == "assistant")
        )).scalars().all()
        assert len(assistant) == 0
```

- [ ] **Step 2: Run to verify fail**

Run (bot env prefix): `cd bot && python3.12 -m pytest tests/test_routers.py::TestProgramRouter::test_view_program_skips_agent_when_taken_over -q`
Expected: FAIL — assistant reply gets written (agent runs).

- [ ] **Step 3: Add takeover guard in view_program_text**

In `bot/src/bot/routers/program.py`, after the user message is saved
(`db.add(chat_msg); await db.flush()`, around line 290) and BEFORE building/running
the agent, insert:

```python
    # ADR-001 superseded: if an organizer took over, the AI stays silent.
    from src.services.support import is_taken_over

    if await is_taken_over(db, UUID(user_id), UUID(event_id)):
        return
```

- [ ] **Step 4: Run test**

Run (bot env prefix): `cd bot && python3.12 -m pytest tests/test_routers.py::TestProgramRouter::test_view_program_skips_agent_when_taken_over -q`
Expected: PASS

- [ ] **Step 5: Full bot suite**

Run (bot env prefix): `cd bot && python3.12 -m pytest tests/ --ignore=tests/e2e --ignore=tests/test_e2e.py -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add bot/src/bot/routers/program.py bot/tests/test_routers.py
git commit -m "feat(bot): mute AI agent when conversation is taken over"
```

---

## Phase 4 — Frontend: user_id, filters, takeover buttons

### Task 7: api-client conversation calls

**Files:**
- Modify: `frontend/src/lib/api-client.ts`
- Test: `frontend/src/lib/api-client.test.ts`

- [ ] **Step 1: Write the failing test**

Add to `frontend/src/lib/api-client.test.ts` (match existing axios-mock-adapter pattern in that file):

```typescript
  it("getConversations hits /admin/conversations with filter", async () => {
    mock.onGet("/admin/conversations").reply(200, { conversations: [], total: 0 })
    const res = await getConversations({ filter: "all" })
    expect(res.total).toBe(0)
  })
```

Add `getConversations` to the import at the top of the test file.

- [ ] **Step 2: Run to verify fail**

Run: `cd frontend && npx vitest run src/lib/api-client.test.ts -t getConversations`
Expected: FAIL — `getConversations` is not exported.

- [ ] **Step 3: Implement api-client functions**

In `frontend/src/lib/api-client.ts`, replace the support block (`getSupportThreads`,
`getSupportMessages`, `sendSupportReply`, `closeSupportThread`, `dismissSupportAttention`
and the `SupportThread`/`SupportMessage`/`SupportThreadList` interfaces) with:

```typescript
export interface Conversation {
  user_id: string
  user_name: string
  user_username: string | null
  user_role: string | null
  last_message: string | null
  last_message_at: string | null
  message_count: number
  unread: boolean
  needs_attention: boolean
  taken_over: boolean
  status: string
}

export interface ConversationMessage {
  id: string
  role: "user" | "assistant" | "organizer"
  content: string
  created_at: string
}

export interface ConversationList {
  conversations: Conversation[]
  total: number
}

export const getConversations = async (params?: { filter?: string; role?: string }): Promise<ConversationList> => {
  const { data } = await apiClient.get<ConversationList>("/admin/conversations", { params })
  return data
}

export const getConversationMessages = async (userId: string): Promise<ConversationMessage[]> => {
  const { data } = await apiClient.get<ConversationMessage[]>(`/admin/conversations/${userId}/messages`)
  return data
}

export const replyToConversation = async (userId: string, text: string): Promise<ConversationMessage> => {
  const { data } = await apiClient.post<ConversationMessage>(`/admin/conversations/${userId}/reply`, { text })
  return data
}

export const releaseConversation = async (userId: string): Promise<{ status: string }> => {
  const { data } = await apiClient.post<{ status: string }>(`/admin/conversations/${userId}/release`)
  return data
}

export const closeConversation = async (userId: string): Promise<{ status: string }> => {
  const { data } = await apiClient.post<{ status: string }>(`/admin/conversations/${userId}/close`)
  return data
}
```

- [ ] **Step 4: Run test + tsc**

Run: `cd frontend && npx vitest run src/lib/api-client.test.ts -t getConversations && npx tsc -b`
Expected: PASS + tsc may report errors in `SupportChat.tsx` (fixed in Task 8). Note them, proceed.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/api-client.ts frontend/src/lib/api-client.test.ts
git commit -m "feat(conversations): frontend api-client conversation calls"
```

### Task 8: Rewrite SupportChat page (user_id, filters, takeover)

**Files:**
- Modify: `frontend/src/pages/SupportChat.tsx`
- Test: `frontend/src/pages/SupportChat.test.tsx` (if exists; else create minimal)

- [ ] **Step 1: Write/adjust the failing test**

If `SupportChat.test.tsx` exists, update it; else create a minimal render test mocking
`getConversations` to return one conversation and assert it renders the user name and
the "Все" filter. Use the existing test patterns from another page test
(`frontend/src/pages/GuestList.test.tsx`) for the QueryClient + mock wrapper.

```typescript
import { render, screen, waitFor } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { describe, it, expect, vi, beforeEach } from "vitest"
import * as api from "../lib/api-client"
import { SupportChat } from "./SupportChat"

describe("SupportChat", () => {
  beforeEach(() => {
    vi.spyOn(api, "getConversations").mockResolvedValue({
      conversations: [{
        user_id: "u1", user_name: "Гость", user_username: "g", user_role: "guest",
        last_message: "привет", last_message_at: null, message_count: 2,
        unread: false, needs_attention: true, taken_over: false, status: "open",
      }],
      total: 1,
    })
    vi.spyOn(api, "getConversationMessages").mockResolvedValue([])
  })

  it("renders a conversation from the list", async () => {
    const qc = new QueryClient()
    render(<QueryClientProvider client={qc}><SupportChat /></QueryClientProvider>)
    await waitFor(() => expect(screen.getByText("Гость")).toBeInTheDocument())
  })
})
```

- [ ] **Step 2: Run to verify fail**

Run: `cd frontend && npx vitest run src/pages/SupportChat.test.tsx`
Expected: FAIL (component still uses old support API).

- [ ] **Step 3: Rewrite SupportChat.tsx**

Rewrite `frontend/src/pages/SupportChat.tsx` to:
- use `getConversations({ filter, role })`, key by `user_id`
- selected id state: `selectedUserId`
- filters: `attention` / `taken_over` / `all` (select), keep role optional later
- messages via `getConversationMessages(selectedUserId)`, render `role` (user left,
  assistant purple "AI-агент", organizer right blue)
- input always available; send via `replyToConversation`
- header buttons: "Вернуть бота" (visible when `taken_over`) → `releaseConversation`;
  "Завершить диалог" → `closeConversation`
- list badges: "Зовёт орга" (needs_attention), "Перехвачен" (taken_over)
- keep the count-based auto-scroll fix already present

(Full component — follow the existing structure of the current SupportChat.tsx, swapping
thread→conversation, sender_type→role, threadId→userId, status filter→filter.)

- [ ] **Step 4: Run test + tsc + eslint**

Run: `cd frontend && npx vitest run src/pages/SupportChat.test.tsx && npx tsc -b && npx eslint src/pages/SupportChat.tsx src/lib/api-client.ts`
Expected: PASS, 0 errors

- [ ] **Step 5: Full frontend suite**

Run: `cd frontend && npx vitest run`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/SupportChat.tsx frontend/src/pages/SupportChat.test.tsx
git commit -m "feat(conversations): admin conversations UI with takeover controls"
```

---

## Phase 5 — Deploy + E2E

### Task 9: Update ADR, deploy, verify on prod

**Files:**
- Modify: `docs/adr/001-unify-support-chat.md`

- [ ] **Step 1: Update ADR-001**

Add a "Superseded by" note at the top of `docs/adr/001-unify-support-chat.md`:
chat_messages is now the source of truth; support_messages deprecated; see
`docs/superpowers/specs/2026-06-03-unified-conversations-design.md`.

- [ ] **Step 2: Full local verification (all layers)**

```bash
cd backend && python3.12 -m pytest tests/ --ignore=tests/test_handlers/test_onboarding.py --ignore=tests/e2e -q && python3.12 -m ruff check app/
cd ../bot && PYTHONPATH="$PWD" BOT_TOKEN=test DATABASE_URL="postgresql+asyncpg://demoday:demoday@localhost:5432/bot_test" REDIS_URL="redis://localhost:6379/1" python3.12 -m pytest tests/ --ignore=tests/e2e --ignore=tests/test_e2e.py -q
cd ../frontend && npx tsc -b && npx eslint . && npx vitest run
```
Expected: all green.

- [ ] **Step 3: Commit + push**

```bash
git add docs/adr/001-unify-support-chat.md
git commit -m "docs(adr): supersede ADR-001 storage decision with chat_messages"
git push origin main
```

- [ ] **Step 4: Wait for CI, then CD applies migration**

CD runs `docker compose ... up -d --build`. Migration 041 applies on backend start.
Verify on prod:
```bash
ssh -i ~/.ssh/evt-ai-key root@85.198.96.191 'docker exec demoday-core-db-1 psql -U demoday demoday -c "\d support_threads" | grep taken_over'
```
Expected: `taken_over | boolean`

- [ ] **Step 5: E2E on prod via real Telegram**

Use `bot/scripts/telegram_e2e.py`:
1. `/start` → role → send a normal question → AI replies (not taken over).
2. From admin API: `POST /admin/conversations/{user_id}/reply` → guest receives
   "Ответ от организатора (...)", thread `taken_over=true`.
3. Send another guest question → AI does NOT reply (muted).
4. `POST /admin/conversations/{user_id}/release` → send guest question → AI replies
   again, with the organizer message visible in `get_support_history` context.
5. Verify `GET /admin/conversations?filter=all` shows the guest with full history.

---

## Self-Review notes

- Spec coverage: full history (Task 5/6 chat_messages), browse all chats (Task 2 lists
  by chat_messages), write any chat (Task 3/4 reply lazily creates thread), filter
  attention (Task 2/8), takeover mutes AI (Task 6), release restores AI (Task 3/4/6),
  AI sees organizer context (Task 5 get_support_history reads organizer role) — all covered.
- `support_messages` is left in place but unwritten (deprecated) — no task deletes it (intentional).
- The bot `_get_or_create_open_thread` already has `with_for_update` (prior work) — reused, not redefined.
- API delivery prefix string matches the existing working format from old support.py.
