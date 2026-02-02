# Sequence Diagrams: AI-first Unconference Navigator

> Версия: 1.2
> Дата: 2 февраля 2026
> Основано на: USM v2.1, C4 v1.1, ER v1.1, RICE v4.0
> Изменения v1.2: Исправлены кросс-ссылки на US/SS (#2, #3, #5), шкала оценки 1–3 (не 1–5), добавлено согласие студента в #5

## Обзор

| # | Сценарий | Сложность | Участники |
|---|----------|-----------|-----------|
| 1 | Профиль интересов + рекомендации (гость) | Средняя | User, Telegram Bot, Core API, Matching, DB |
| 2 | Подтверждение участия (эксперт/студент) | Средняя | User, Telegram Bot, Core API, DB |
| 3 | Оценка проекта + критерии | Средняя | User, Telegram Bot, Core API, DB |
| 4 | Напоминания о дедлайнах (async) | Средняя | Worker, Core API, Telegram, DB |
| 5 | Follow-up «хочу контакт» | Низкая | User, Telegram Bot, Core API, DB |
| 6 | Роль организатора по приглашению | Средняя | User, Telegram Bot, Core API, DB |
| 7 | Q&A-помощник (гость/бизнес) | Средняя | User, Telegram Bot, Core API, Matching, AI, DB |
| 8 | Бизнес-профилирование + рекомендации | Средняя | User, Telegram Bot, Core API, Matching, DB |

---

## 1. Профиль интересов + рекомендации (гость)

### Контекст

**User Story:** US-002, US-009, SS-002, SS-003
**Участники:** Гость, Telegram Bot, Core API, Matching, DB
**CustDev:** H8 (RICE 27, 100%), H16 (RICE 66, 60%) — «кнопки тематик + свободный текст, 5–10 мин»

### Диаграмма

```mermaid
sequenceDiagram
    participant U as Гость
    participant B as Telegram Bot
    participant A as Core API
    participant M as Matching & Q&A
    participant D as Database

    Note over U,B: Шаг 1: Подтип гостя (H16)
    B->>U: Выберите подтип: Абитуриент / AI-практик / Другое
    U->>B: Выбор подтипа
    B->>A: PATCH /users/me (guest_subtype)
    A->>D: Update user.guest_subtype
    D-->>A: OK

    Note over U,B: Шаг 2: Кнопки тематик
    B->>U: Выберите интересующие тематики (checkboxes)
    U->>B: Выбор тематик (NLP, CV, Agents...)
    B->>A: POST /profile/interests (tags[])
    A->>D: Save user_interests
    D-->>A: OK

    Note over U,B: Шаг 3: Свободный текст (опц.)
    B->>U: Уточните интересы (свободный текст)
    U->>B: "LLM, RAG, healthcare"
    B->>A: POST /profile/interests/keywords
    A->>D: Save user_interest_keywords
    D-->>A: OK

    Note over A,M: Генерация рекомендаций
    A->>M: Build recommendations (tags + keywords)
    M->>D: Read projects/tags
    D-->>M: Projects data
    M-->>A: Recommended list (10–15 проектов)
    A-->>B: Recommendations
    B-->>U: Персональная подборка проектов

    alt Уточнение интересов
        U->>B: Изменить теги/ключевые слова
        B->>A: PATCH /profile/interests
        A->>M: Recompute recommendations
        M-->>A: Updated list
        A-->>B: New recommendations
        B-->>U: Обновлённый список
    end
```

### Примечания
- Двухшаговое профилирование: кнопки (быстрый выбор) → свободный текст (уточнение).
- Подтип гостя влияет на ранжирование рекомендаций (абитуриенты видят больше EdTech).
- Пересчёт рекомендаций должен быть быстрым (пик 100 пользователей).

---

## 2. Подтверждение участия (эксперт/студент)

### Контекст

**User Story:** US-005, US-007, SS-003, SS-004
**Участники:** Пользователь, Telegram Bot, Core API, DB

### Диаграмма

```mermaid
sequenceDiagram
    participant U as User
    participant B as Telegram Bot
    participant A as Core API
    participant D as Database

    U->>B: Подать заявку/подтвердить участие
    B->>A: POST /participation-requests
    A->>D: Insert participation_request
    D-->>A: OK
    A-->>B: Status=submitted
    B-->>U: Заявка отправлена

    alt Организатор подтверждает
        A->>D: Update status=confirmed
        D-->>A: OK
        A-->>B: Notify confirmed
        B-->>U: Подтверждение участия
    end
```

### Примечания
- В MVP статусы: submitted → confirmed.

---

## 3. Оценка проекта + критерии

### Контекст

**User Story:** US-019
**Участники:** Эксперт, Telegram Bot, Core API, DB

### Диаграмма

```mermaid
sequenceDiagram
    participant U as Expert
    participant B as Telegram Bot
    participant A as Core API
    participant D as Database

    U->>B: Оценить проект (7 критериев, 1–3 + коммент)
    B->>A: POST /project-reviews
    A->>D: Insert review
    D-->>A: OK
    A-->>B: Review saved

    opt Трековые критерии
        U->>B: Оценка по критериям
        B->>A: POST /project-reviews/{id}/items
        A->>D: Insert criteria scores
        D-->>A: OK
        A-->>B: Criteria saved
    end
```

### Примечания
- 7 критериев, каждый 1–3 (веса 6×10% + 1×20%). Итого overall_score = взвешенный % (0–100).
- Подсказки по критериям показываются в боте перед оценкой.
- Эксперт сам формулирует вопросы — AI-подсказки для Q&A НЕ предлагаются (интервью #2: «вопросы от человека должны исходить»).

---

## 4. Напоминания о дедлайнах (async)

### Контекст

**User Story:** SS-005, SS-007, SS-016
**Участники:** Core API, Worker, DB, Telegram

### Диаграмма

```mermaid
sequenceDiagram
    participant A as Core API
    participant D as Database
    participant W as Notification Worker
    participant T as Telegram Platform

    A-)W: Enqueue reminders
    W->>D: Fetch pending reminders
    D-->>W: Reminders list
    W->>T: Send message
    T-->>W: OK
    W->>D: Update status=sent

    Note over W,T: Типы: deadline, reminder, followup, feedback_request, timing_shift
```

### Примечания
- В день события и после — повторная отправка формы обратной связи.
- Уведомления о сдвигах тайминга (SS-016, USM v2.1).

---

## 5. Follow-up «хочу контакт»

### Контекст

**User Story:** US-020, US-021
**Участники:** Пользователь (гость/бизнес/эксперт), Telegram Bot, Core API, DB
**CustDev:** H15 депр. (RICE 12, гость 1/5) — только запрос контакта, НЕ 1:1 встречи.

### Диаграмма

```mermaid
sequenceDiagram
    participant U as User
    participant B as Telegram Bot
    participant A as Core API
    participant D as Database

    U->>B: Отметить "хочу контакт" по проекту
    B->>A: POST /contact-requests
    A->>D: Insert contact_request (status=requested)
    D-->>A: OK
    A-->>B: Status=requested
    B-->>U: Запрос принят

    Note over A,D: Согласие студента (US-021)
    A->>D: Find project author
    D-->>A: Author user_id
    A-->>B: Notify author
    B-->>B: "Партнёр [роль] хочет связаться. Разрешаешь?"

    alt Студент разрешает
        B->>A: PATCH /contact-requests/{id} (student_consent=true)
        A->>D: Update status=approved → shared
        D-->>A: OK
        A-->>B: Контакт автора проекта
        B-->>U: Контактные данные (email/telegram)
    else Студент отказывает
        B->>A: PATCH /contact-requests/{id} (student_consent=false)
        A->>D: Update status=declined
        D-->>A: OK
        A-->>B: Уведомление
        B-->>U: Автор пока не готов делиться контактом
    end
```

### Примечания
- Это запрос контакта, а не запись на 1:1 встречу.
- Требуется согласие студента (US-021, 152-ФЗ). Организатор может модерировать дополнительно.
- Доступно ролям: Гость, Бизнес/партнёр, Эксперт.

---

## 6. Роль организатора по приглашению

### Контекст

**User Story:** US-002, SS-001
**Участники:** Пользователь, Telegram Bot, Core API, DB

### Диаграмма

```mermaid
sequenceDiagram
    participant U as User
    participant B as Telegram Bot
    participant A as Core API
    participant D as Database

    U->>B: Выбирает роль «Организатор»
    B->>U: Запрос кода приглашения
    U->>B: Вводит код
    B->>A: POST /role-invites/accept
    A->>D: Validate invite code
    D-->>A: Invite valid
    A->>D: Assign organizer role
    D-->>A: OK
    A-->>B: Role assigned
    B-->>U: Доступ организатора подтверждён

    alt Кода нет — запрос назначения
        U->>B: Запросить доступ
        B->>A: POST /access-requests
        A->>D: Save access request
        D-->>A: OK
        A-->>B: Request received
        B-->>U: Ожидайте назначения
    end
```

### Примечания
- Назначение админом может происходить вне бота; уведомление приходит через Telegram.

---

## 7. Q&A-помощник (гость/бизнес)

### Контекст

**User Story:** US-012, H10 (RICE 50, 100%)
**Участники:** Гость или Бизнес/партнёр, Telegram Bot, Core API, Matching, AI, DB
**CustDev:** Гость хочет подсказки (интервью #4: 5/5). Эксперт — нет (интервью #2: «от человека»).

### Диаграмма

```mermaid
sequenceDiagram
    participant U as Гость/Бизнес
    participant B as Telegram Bot
    participant A as Core API
    participant M as Matching & Q&A
    participant AI as LLM (Xray)
    participant D as Database

    U->>B: Открыть проект из рекомендаций
    B->>A: GET /projects/{id}
    A->>D: Read project (summary, tags, materials)
    D-->>A: Project data
    A-->>B: Карточка проекта
    B-->>U: Описание, стек, стадия

    U->>B: "Подготовь вопросы для Q&A"
    B->>A: POST /qa-suggestions
    A->>D: Check cache (user_id + project_id)
    D-->>A: Not found

    A->>M: Generate Q&A (profile + project context)
    M->>AI: Prompt: вопросы под профиль гостя/бизнеса
    AI-->>M: 3–5 подсказок вопросов
    M-->>A: QA suggestions

    A->>D: Save qa_suggestions
    D-->>A: OK
    A-->>B: Подсказки вопросов
    B-->>U: "Вот вопросы, которые можно задать:"
```

### Примечания
- Подсказки кэшируются: при повторном запросе возвращаются из БД.
- Контекст генерации: профиль пользователя (интересы + подтип/бизнес-профиль) + summary проекта.
- Для бизнес-партнёров вопросы ориентированы на: стадия, монетизация, команда, IP.

---

## 8. Бизнес-профилирование + рекомендации

### Контекст

**User Story:** H14 (RICE 23, 100%), H17 (RICE 23, 100%)
**Участники:** Бизнес/партнёр, Telegram Bot, Core API, Matching, DB

### Диаграмма

```mermaid
sequenceDiagram
    participant U as Бизнес/Партнёр
    participant B as Telegram Bot
    participant A as Core API
    participant M as Matching & Q&A
    participant D as Database

    Note over U,B: Шаг 1: Бизнес-профиль
    B->>U: Выберите отрасль (кнопки)
    U->>B: FinTech
    B->>U: Формат партнёрства (кнопки)
    U->>B: Инвестиции
    B->>U: Предпочитаемая стадия (кнопки)
    U->>B: MVP/Pilot
    B->>U: Дополнительно (свободный текст)
    U->>B: "Ищу NLP-проекты для FinTech с командой 3+"

    B->>A: POST /business-profiles
    A->>D: Save business_profile
    D-->>A: OK

    Note over U,B: Шаг 2: Тематики (как у гостей)
    B->>U: Выберите тематики (checkboxes)
    U->>B: NLP, FinTech, Agents
    B->>A: POST /profile/interests (tags[])
    A->>D: Save user_interests
    D-->>A: OK

    Note over A,M: Бизнес-матчинг
    A->>M: Build recommendations (tags + business_profile)
    M->>D: Read projects (by tags, stage, track)
    D-->>M: Projects data
    M-->>A: Ranked list (бизнес-релевантность)
    A-->>B: Recommendations
    B-->>U: Подборка проектов под бизнес-запрос
```

### Примечания
- Бизнес-профиль хранится отдельно от user_interests (разные сущности: business_profiles vs user_interests).
- Рекомендации учитывают и тематики (user_interests), и бизнес-контекст (partnership_format, stage).
- Follow-up пакет (H17) отправляется через Notification Worker после DD.

---

## Приложения

### Участники (из C4 v1.1)

| ID | Название | Тип | Описание |
|---|---|---|---|
| User | Пользователь | Actor | Организатор/студент/эксперт/гость/бизнес |
| Telegram Bot | Container | UI | Диалоговый интерфейс |
| Core API | Container | Service | Бизнес-логика |
| Matching & Q&A | Container | Service | Рекомендации, Q&A-подсказки, бизнес-матчинг |
| Database | ContainerDb | Data | Основные данные |
| Notification Worker | Container | Async | Напоминания, follow-up, рассылка ОС |
| Telegram Platform | System_Ext | External | Канал сообщений |
| LLM (Xray) | System_Ext | External | AI-генерация через Xray proxy |

### Соглашения

- `->>` / `-->>` — синхронные
- `-)` / `--)` — асинхронные
- `-x` — ошибка

### Изменения v1.1 → v1.2

| Что изменено | Описание |
|---|---|
| Сценарий 2 | Исправлены ссылки: US-008/009/010 → US-005, US-007, SS-003, SS-004 |
| Сценарий 3 | Исправлены ссылки: US-014/015/015a → US-019. Шкала: 1–5 → 1–3 (7 критериев) |
| Сценарий 5 | Исправлены ссылки: US-017/SS-008 → US-020, US-021. Добавлен шаг согласия студента |

### Изменения v1.0 → v1.1

| Что изменено | Описание |
|---|---|
| Сценарий 1 | Разбит на 3 шага: подтип → кнопки → текст (CustDev H16) |
| Сценарий 5 | Уточнено: запрос контакта, НЕ 1:1 встречи (H15 депр.) |
| Сценарий 7 | **Новый:** Q&A-помощник для гостей/бизнеса (H10) |
| Сценарий 8 | **Новый:** Бизнес-профилирование + рекомендации (H14) |
| Участники | +LLM (Xray), роли обновлены до 5 |
