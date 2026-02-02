# Research: Business Partner Profiling & Personalized Program

**Date**: 2026-02-02
**Feature**: EPIC-006 (002-business-profiling)

---

## R1: Profile Extraction from Free Text

**Question**: How to extract structured business profile from free-text input?

**Decision**: Use existing `llm_client.send_chat_completion()` with JSON mode.

**Rationale**:
- Already proven in EPIC-002 (clustering_service.py) — handles retries, fallback model, JSON parsing
- OpenRouter API with GPT-4.1 or Claude as fallback
- JSON mode ensures structured output matching BusinessProfile schema

**Implementation**:
```python
PROFILE_EXTRACTION_PROMPT = """
Extract a structured business profile from the user's description.
Output JSON with fields:
- objective: "investment" | "hiring" | "technology" | "partnership"
- industries: list of relevant industries (max 5)
- tech_stack: list of technologies mentioned (max 10)
- project_stages: list from ["idea", "mvp", "early_traction", "scaling", "mature"]
- collaboration_format: free text describing desired collaboration
- parsed_interests: list of extracted interest keywords (max 10)

If a field cannot be determined, use empty list or null.
"""
```

**Alternatives Considered**:
- Regex/keyword extraction: Too brittle, misses synonyms and context
- Separate NLP pipeline: Over-engineering, YAGNI

---

## R2: Project-Profile Matching Algorithm

**Question**: How to rank 330 projects by relevance to business profile?

**Decision**: Two-stage approach: tag-based filtering + LLM re-ranking.

**Rationale**:
- Tag-based filtering is fast and deterministic (existing ProjectTag model)
- LLM re-ranking adds business context (investor vs HR vs tech partner)
- Graceful degradation: if LLM fails, return tag-filtered results without ranking

**Implementation**:
1. **Stage 1 (Filtering)**: Match profile.industries/tech_stack against project tags
   - Score = count of matching tags / total profile criteria
   - Keep top 30 projects (or all if < 30 match)

2. **Stage 2 (LLM Ranking)**: For top candidates, ask LLM to rank by business relevance
   - Input: profile summary + list of project summaries (title, description, tags)
   - Output: JSON array with project_id + relevance_score (0-100) + explanation

**Alternatives Considered**:
- Pure LLM (send all 330 projects): Token limit exceeded, too slow, expensive
- Pure tag matching: Misses business context (investor cares about stage, HR about team)
- Embedding similarity: Requires vector DB setup, over-engineering for demo

---

## R3: Telegram Conversation Flow Design

**Question**: How to structure multi-step profiling in Telegram?

**Decision**: ConversationHandler with 6 states, following EPIC-001/002 patterns.

**States**:
```
CHOOSE_OBJECTIVE → CHOOSE_CRITERIA → FREE_TEXT_INPUT → CONFIRM_PROFILE →
VIEW_RECOMMENDATIONS → PROJECT_DETAIL
```

**Rationale**:
- Matches existing patterns (start.py: 3 states, clustering.py: 10 states)
- Each state handles one question/screen
- Easy to add/remove steps without refactoring

**Flow**:
1. `CHOOSE_OBJECTIVE`: 4 buttons (Инвестиции/Найм/Технология/Партнёрство)
2. `CHOOSE_CRITERIA`: Dynamic buttons based on objective (industries, stages, etc.)
3. `FREE_TEXT_INPUT`: Optional, MessageHandler for text + "Пропустить" button
4. `CONFIRM_PROFILE`: Show extracted profile, "Подтвердить" / "Исправить" buttons
5. `VIEW_RECOMMENDATIONS`: Paginated list of projects (5 per page)
6. `PROJECT_DETAIL`: Single project card with "Подробнее" / "Назад" / "Добавить в программу"

**Alternatives Considered**:
- Single long message with all questions: Poor UX, no validation per step
- Wizard without states: Harder to handle interruptions/corrections

---

## R4: Callback Data Encoding

**Question**: How to fit complex data in 64-byte callback limit?

**Decision**: Compact prefix + ID encoding.

**Patterns**:
```
bp:obj:inv         # business_profile:objective:investment (12 bytes)
bp:ind:fin,nlp     # industries selection (14 bytes)
bp:stg:mvp,scale   # stages (13 bytes)
bp:confirm:yes     # confirm profile (14 bytes)
bp:rec:page:2      # recommendations page 2 (13 bytes)
bp:proj:<uuid8>    # first 8 chars of project UUID (17 bytes)
```

**Rationale**:
- Follows EPIC-002 pattern (cl:room:, cl:approve:)
- UUID truncation safe because scoped to user's session
- Easily parseable with split(":")

---

## R5: Profile Persistence Strategy

**Question**: Should profiles be versioned? How to handle modifications?

**Decision**: Single active profile per user+event, updated in place.

**Rationale**:
- YAGNI: Version history not needed for demo
- Spec says "Profile modifications MUST trigger recommendation regeneration" — simpler with single record
- `updated_at` timestamp tracks last modification

**Schema**:
```sql
CREATE TABLE business_profiles (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    event_id UUID REFERENCES events(id),
    objective VARCHAR(20) NOT NULL,  -- enum
    industries TEXT[],
    tech_stack TEXT[],
    project_stages TEXT[],
    collaboration_format TEXT,
    free_text_raw TEXT,
    free_text_parsed JSONB,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    UNIQUE(user_id, event_id)
);
```

---

## R6: Graceful Degradation

**Question**: What happens when LLM is unavailable?

**Decision**: Tiered fallback.

**Scenarios**:
1. **Profile extraction fails**: Offer structured-only input (buttons for all fields)
2. **Recommendation ranking fails**: Return tag-filtered results without relevance scores
3. **Both fail**: Show message "AI-сервис временно недоступен. Попробуйте позже."

**Rationale**:
- Constitution II: "CRUD-функции НЕ ДОЛЖНЫ зависеть от LLM API"
- Profiling via buttons is CRUD (no AI needed)
- Ranking without AI still provides value (tag-matched projects)

---

## R7: Existing Dependencies

**Confirmed available**:
- `llm_client.send_chat_completion()` — async, retries, JSON mode ✓
- `Project` model with tags relationship ✓
- `project_service.get_projects_by_event()` ✓
- `Tag` model with name field ✓
- `User` model with telegram_user_id ✓
- `Event` model for current event ✓
- `keyboards.py` pattern for InlineKeyboardMarkup ✓

**To be created**:
- `BusinessProfile` model
- `ProjectRecommendation` model
- `profile_service.py`
- `recommendation_service.py`
- `business_profiling.py` handler
- Alembic migration 003
