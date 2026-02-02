# Data Model: Профилирование и программа для гостей (EPIC-005)

**Date**: 2026-02-02
**Branch**: `005-guest-profiling`

## Overview

2 новые таблицы + использование 4 существующих. Следуем паттерну из EPIC-002/003: UUID PK, Base с `id` + `created_at`, async SQLAlchemy 2.0.

## New Entities

### guest_profiles

Профиль интересов гостя. Один профиль на пользователя на событие.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, default uuid4 | |
| user_id | UUID | FK → users.id, NOT NULL | Гость |
| event_id | UUID | FK → events.id ON DELETE CASCADE, NOT NULL | Событие |
| selected_tags | JSONB | NOT NULL, default [] | Массив строк — теги выбранные кнопками |
| extracted_tags | JSONB | NOT NULL, default [] | Массив строк — теги извлечённые AI из текста |
| keywords | JSONB | NOT NULL, default [] | Ключевые слова из свободного текста (для LLM re-ranking) |
| raw_text | TEXT | NULLABLE | Сырой текст свободного ввода гостя |
| created_at | TIMESTAMPTZ | NOT NULL, server_default now() | |
| updated_at | TIMESTAMPTZ | NOT NULL, server_default now(), onupdate now() | |

**Constraints**:
- UNIQUE(user_id, event_id) — один профиль на гостя на событие
- Index on (event_id) — для выборки по событию

**Notes**:
- `selected_tags` и `extracted_tags` хранятся как JSONB массивы строк (["NLP", "FinTech"]) а не как FK на tags таблицу. Причина: теги профиля могут не совпадать 1:1 с существующими тегами проектов (AI может извлечь "антифрод" которого нет в tags).
- `keywords` — дополнительные ключевые слова не являющиеся тегами, для передачи в LLM re-ranking.

### recommendations

Персональная подборка проектов для гостя. Один набор рекомендаций привязан к конкретному профилю.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, default uuid4 | |
| guest_profile_id | UUID | FK → guest_profiles.id ON DELETE CASCADE, NOT NULL | Профиль |
| project_id | UUID | FK → projects.id ON DELETE CASCADE, NOT NULL | Проект |
| relevance_score | FLOAT | NOT NULL | Итоговый скор релевантности |
| category | VARCHAR(20) | NOT NULL | "must_visit" или "if_time" |
| rank | INTEGER | NOT NULL | Порядковый номер в подборке (1-15) |
| llm_summary | TEXT | NULLABLE | AI-сгенерированное краткое описание |
| created_at | TIMESTAMPTZ | NOT NULL, server_default now() | |

**Constraints**:
- UNIQUE(guest_profile_id, project_id) — один проект один раз в подборке
- Index on (guest_profile_id) — для получения подборки

## Existing Entities (used, not modified)

### users (EPIC-001)
- `guest_subtype` — уже есть, используется для адаптации подборки
- Связь: `user.id → guest_profiles.user_id`

### tags (EPIC-002)
- `name` — используется как источник для кнопок профилирования
- Не создаём junction table guest_profile_tags — теги хранятся в JSONB

### projects (EPIC-002)
- `title, description, author, telegram_contact` — для отображения в подборке
- Связь через `project_tags → tags` — для tag overlap scoring

### rooms (EPIC-002)
- `name, display_order` — для отображения зала в подборке
- Связь через `room_projects → projects` — для определения зала проекта и конфликтов

## ER Diagram (new entities only)

```
users 1──* guest_profiles *──1 events
                |
                * (1 profile → many recommendations)
                |
          recommendations *──1 projects
```

## SQLAlchemy Models

### GuestProfile

```python
# backend/app/models/guest_profile.py
class GuestProfile(Base):
    __tablename__ = "guest_profiles"
    __table_args__ = (
        UniqueConstraint("user_id", "event_id", name="uq_guest_profiles_user_event"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True
    )
    selected_tags: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    extracted_tags: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    keywords: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    recommendations = relationship("Recommendation", back_populates="guest_profile", cascade="all, delete-orphan")
```

### Recommendation

```python
# backend/app/models/recommendation.py
class Recommendation(Base):
    __tablename__ = "recommendations"
    __table_args__ = (
        UniqueConstraint("guest_profile_id", "project_id", name="uq_recommendations_profile_project"),
    )

    guest_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("guest_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    relevance_score: Mapped[float] = mapped_column(Float, nullable=False)
    category: Mapped[str] = mapped_column(String(20), nullable=False)  # "must_visit" | "if_time"
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    llm_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    guest_profile = relationship("GuestProfile", back_populates="recommendations")
    project = relationship("Project")
```

## Migration: 004_guest_profiling

```python
revision = "004"
down_revision = "003"

def upgrade():
    op.create_table("guest_profiles", ...)
    op.create_table("recommendations", ...)

def downgrade():
    op.drop_table("recommendations")
    op.drop_table("guest_profiles")
```
