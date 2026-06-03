# Дизайн: единая переписка «гость ↔ бот ↔ организатор»

**Дата:** 2026-06-03
**Автор:** Дмитрий Горбунов
**Статус:** Согласован, готов к плану реализации

## Проблема

Организатор видит только сообщения support-эскалации (после нажатия `/support`),
а не весь диалог гостя с AI-агентом. Нужно:

1. Орг видит **весь** диалог гостя с ботом (с самого начала, а не от запроса в поддержку).
2. Орг видит **все** чаты, даже без запроса в поддержку.
3. Орг может **писать в любой** чат, даже если его не звали.
4. Чаты, где орга позвали (`/support`), можно **фильтровать** в админке.
5. Когда орг пишет — он **перехватывает** чат: AI замолкает в этом чате.
6. Орг может **завершить перехват** («Вернуть бота») — бот снова отвечает.
7. После возврата AI-агент **видит весь диалог с оргом** в своём контексте.

## Решение (обзор)

`chat_messages` — единственный источник правды для сообщений. `support_threads` —
оверлей метаданных диалога (1 строка на user+event). `support_messages` —
депрекейт. Организатор работает в админке по `user_id` (диалог = гость).

Это **разворачивает ADR-001** (там стором был `support_messages`). ADR-001
обновляется: метаданные треда остаются, но сообщения переезжают в `chat_messages`.

**Известный долг:** `support_threads` концептуально стоит переименовать в
`conversations` — отдельной задачей (миграция таблицы задевает обе ORM-проекции).

## Модель данных

### `chat_messages` (источник правды сообщений)
Существует. Поля: `id, user_id, event_id, role, content, created_at`.
- `role`: `user` | `assistant` (AI) | `organizer` (**новая роль**).
- Орг пишет сюда же (role=organizer). Support и обычный диалог — одна лента.

### `support_threads` (оверлей метаданных, 1 строка на user+event)
Существует. Используется как состояние диалога:
- `needs_attention` (есть) — гость нажал `/support`. Фильтр «позвали поддержку».
- `status` open/closed (есть) — «Завершить диалог».
- `taken_over` (**новое поле**, bool, default false, server_default 'false') —
  орг перехватил, бот молчит.
- Строка создаётся лениво: гость зовёт `/support` ИЛИ орг впервые пишет/перехватывает.
- Миграция: `ALTER TABLE support_threads ADD COLUMN taken_over boolean NOT NULL DEFAULT false`.
  Зеркальное поле в bot ORM-модели `support_thread.py`.

### `support_messages`
Депрекейт. Перестаём писать (вчерашний путь `add_user_support_message` →
`SupportMessage` отключается, пишем в `chat_messages`). Таблица остаётся для истории.

## Поток данных

### Гость пишет боту (обычный режим) — `bot/src/bot/routers/program.py`
1. Сохранить `chat_messages(role=user)`.
2. Прочитать `support_threads.taken_over` для (user, event).
3. `taken_over=false` или треда нет → AI-агент отвечает, пишет `chat_messages(role=assistant)`.
4. `taken_over=true` → **AI пропускается**, сообщение только сохранено. Гость ждёт человека.

### Гость зовёт `/support` — `bot/src/bot/routers/support.py`
- `support_text` пишет `chat_messages(role=user)` + ставит `support_threads.needs_attention=true`
  (lazy get-or-create треда, `with_for_update`).
- Сервис `bot/src/services/support.py`: `add_user_support_message` меняет цель записи —
  теперь создаёт `ChatMessage(role=user)` вместо `SupportMessage`, тред используется только
  для `needs_attention`/state. Сигнатура и вызов из роутера не меняются.

### Орг пишет из админки
1. `POST /admin/conversations/{user_id}/reply` → `chat_messages(role=organizer, content)`.
2. `taken_over=true`, `needs_attention=false`, `updated_at=now` на треде (lazy create).
3. Доставка гостю через `bot_messenger`: `«Ответ от организатора (Имя): …»` (префикс, работает).

### Орг жмёт «Вернуть бота»
1. `POST /admin/conversations/{user_id}/release` → `taken_over=false`.
2. Следующее сообщение гостя → AI отвечает.

### Орг «Завершить диалог»
- `POST /admin/conversations/{user_id}/close` → `status=closed`, `taken_over=false`.

### Контекст AI-агента — `bot/src/bot/routers/program.py` + `agent.py`
- При каждом запуске агент строит `message_history` из `chat_messages`
  (последние N, tiebreaker по id), а не из FSM `program_chat`.
- `role=organizer` маппится в историю как реплика человека-организатора, так что
  после возврата управления AI видит, что отвечал орг.

## API (backend) — переименование в `/admin/conversations/*`

Все эндпоинты переезжают с `/admin/support/*` (thread_id) на `/admin/conversations/*` (user_id):

- `GET /admin/conversations` — список: distinct гости из `chat_messages`
  LEFT JOIN `support_threads`. Поля: `user_id, user_name, user_username, user_role,
  last_message, last_message_at, message_count, needs_attention, taken_over, status, unread`.
  Query-фильтры: `filter=attention|taken_over|all`, `role=guest|business|expert`.
  - `unread` (определение): последнее сообщение в `chat_messages` для (user,event)
    имеет `role=user` (т.е. гость написал, ответа от assistant/organizer ещё нет).
  - `message_count` = число строк `chat_messages` для (user,event).
  - `last_message` / `last_message_at` = из последней строки `chat_messages`.
  - гости без `support_threads`: `needs_attention=false, taken_over=false, status='open'` (дефолты).
- `GET /admin/conversations/{user_id}/messages` — лента из `chat_messages`
  (user/assistant/organizer), хронологически.
- `POST /admin/conversations/{user_id}/reply` — organizer-сообщение в chat_messages,
  `taken_over=true`, доставка в Telegram, `needs_attention=false`.
- `POST /admin/conversations/{user_id}/release` — `taken_over=false`.
- `POST /admin/conversations/{user_id}/close` — `status=closed, taken_over=false`.

Старые `/admin/support/*` роуты удаляются. api-client и фронт обновляются.

## Frontend — `frontend/src/pages/SupportChat.tsx`

- Идентификатор диалога: `user_id` (не thread_id).
- Фильтры: «Позвали поддержку» (attention) / «Перехваченные» (taken_over) / «Все» / по роли.
- Лента рендерит 3 типа: user (слева), assistant (фиолет «AI-агент»), organizer
  (справа, синий). Рендер уже поддерживает sender_type, адаптировать под role.
- Бейджи в списке: «Зовёт орга» (needs_attention), «Перехвачен» (taken_over).
- Кнопки в шапке: «Вернуть бота» (если taken_over), «Завершить диалог».
- Поле ввода доступно всегда (орг может писать в любой чат), не только при open.

## Обработка ошибок

- Доставка орг-ответа упала → сообщение гостя/орга в `chat_messages` сохранено; орг увидит при поллинге.
- Гонка создания треда → `with_for_update` + lazy get-or-create (реализовано).
- Орг пишет в чат без треда → создаётся лениво.
- Агент: лимит N последних сообщений + tiebreaker по id (реализовано в get_support_history).
- `bot_messenger` падает → лог + «не доставлено» в админке, запись в БД остаётся.

## Тестирование (TDD)

**Bot (pytest, реальная БД):**
- `taken_over=true` → агент пропускается, сообщение сохранено.
- `taken_over=false` → агент отвечает.
- агент строит контекст из `chat_messages` включая role=organizer.
- get-or-create треда при перехвате/поддержке.

**Backend (pytest, sqlite):**
- `GET /conversations` мержит chat_messages + thread-метаданные; фильтры attention/taken_over/all/role.
- список включает гостей без support-запроса (только chat_messages).
- `reply` пишет organizer-сообщение + taken_over=true + needs_attention=false + доставка.
- `release` снимает taken_over. `close` ставит closed + taken_over=false.

**Frontend (vitest):**
- фильтры рендерят правильные подмножества.
- «Вернуть бота» видна только при taken_over.
- три типа сообщений рендерятся.

## Фазы реализации (для плана)

Порядок, чтобы CI/CD не падал посередине:
1. **Миграция + backend модель** — `taken_over` колонка + поле в обеих ORM-моделях.
2. **Backend conversation_service + API** — список/лента из chat_messages, reply/release/close (TDD).
3. **Bot** — takeover-guard в program.py, контекст из chat_messages, `/support` в chat_messages (TDD).
4. **Frontend** — переход на user_id, фильтры, кнопки (TDD vitest).
5. **Деплой** — миграция применяется на проде, проверка E2E.

## Файлы

**Создать:**
- `backend/alembic/versions/041_conversation_takeover.py` (taken_over column)

**Изменить (backend):**
- `app/models/support_thread.py` (+taken_over)
- `app/api/admin/support.py` → переименовать в `conversations.py`, новые роуты по user_id
- `app/services/admin/support_service.py` → переименовать в `conversation_service.py`:
  чтение chat_messages, list/messages/reply/release/close
- `app/schemas/support.py` → conversation-схемы
- `app/main.py` / router registration

**Изменить (bot):**
- `src/models/support_thread.py` (+taken_over зеркально)
- `src/bot/routers/program.py` (taken_over guard; контекст из chat_messages)
- `src/bot/routers/support.py` (`/support` пишет chat_messages)
- `src/services/support.py` (запись в chat_messages, takeover-helpers)
- `src/agent/agent.py` (история из chat_messages)

**Изменить (frontend):**
- `src/pages/SupportChat.tsx` (user_id, фильтры, кнопки)
- `src/lib/api-client.ts` (conversation-вызовы)

**Обновить:**
- `docs/adr/001-unify-support-chat.md` (супрессия решения про support_messages)
