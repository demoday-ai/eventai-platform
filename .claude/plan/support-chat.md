# Feature: Support Chat (bot <-> admin)

## Design (agreed with user)

Двусторонний чат между участниками (бот) и организаторами (админка).

### Bot side:
- Кнопка "Позвать организатора" в меню бота
- При нажатии: бот прекращает AI-ответы, создает SupportThread
- Пока тред открыт: все сообщения пользователя идут в тред, не в AI-агент
- Ответы организатора приходят от бота

### Admin side:
- Список тредов с badge "Требует внимания"
- Открыть тред -> история -> поле ответа
- Организатор может сам создать тред с любым пользователем
- Кнопка "Закрыть диалог"

### Switching back to AI:
- A) Организатор закрывает тред из админки -> пользователю: "Организатор завершил диалог"
- C) Пользователь нажимает "Вернуться к боту" сам

### Context handoff:
- При возврате в AI-режим: ПОЛНАЯ дословная история переписки из треда подгружается в контекст агента
- Агент видит что обсуждалось и продолжает с учетом контекста

### Technical constraints (from NFR):
- Polling каждые 3 сек в админке (не WebSocket)
- До 30-50 одновременных диалогов в день DD
- Один разработчик - простые решения

## Implementation Plan

### Step 1: DB Models + Migration
- `SupportThread`: id, user_id, event_id, status (open/closed), closed_by (user/organizer), created_at, updated_at
- `SupportMessage`: id, thread_id, sender_type (user/organizer), sender_id, text, created_at
- Migration 034

### Step 2: Backend Service
- `support_service.py`: create_thread, get_threads, get_messages, send_reply, close_thread, get_unread_count
- Thread dedup: один открытый тред на пользователя

### Step 3: Backend API
- GET /admin/support/threads (list, filter by status)
- GET /admin/support/threads/:id/messages
- POST /admin/support/threads/:id/reply
- POST /admin/support/threads/:id/close
- POST /admin/support/threads (create thread to specific user)
- GET /admin/support/unread-count (lightweight for badge polling)

### Step 4: Bot Handler
- New `chat_handler.py` with ConversationHandler
- State SUPPORT_CHAT: all text goes to thread
- Кнопка "Позвать организатора" -> create thread -> enter SUPPORT_CHAT
- Кнопка "Вернуться к боту" -> close thread from user side -> return to VIEW_PROGRAM
- On thread close by organizer: next message returns to AI-agent
- Context injection: load thread messages into agent context on return

### Step 5: Frontend
- New route /support-chat
- SupportChat.tsx: two-panel layout (ConversationList + ChatPanel)
- Polling refetchInterval: 3000ms
- NotificationBadge in Sidebar (unread count)
- Организатор может создать новый тред к конкретному пользователю

### Step 6: Tests
- Backend: models, service, API lifecycle
- Bot: conversation flow (open -> messages -> close -> AI context)
- Frontend: component rendering, polling, message send

### Key files to create:
- backend/app/models/support_thread.py
- backend/app/models/support_message.py
- backend/app/services/admin/support_service.py
- backend/app/api/admin/support.py
- backend/app/bot/handlers/chat_handler.py
- backend/alembic/versions/034_support_chat.py
- frontend/src/pages/SupportChat.tsx
- frontend/src/lib/api-client.ts (extend)
- frontend/src/components/layout/Sidebar.tsx (badge)

### Key files to modify:
- backend/app/bot/handlers/start.py (add button, integrate chat_handler)
- backend/app/bot/keyboards.py (support button)
- backend/app/bot/app.py (register handler)
- backend/app/models/__init__.py (register models)
- frontend/src/App.tsx (new route)

