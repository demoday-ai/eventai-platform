# Feature Specification: Business Partner Profiling & Personalized Program

**Feature Branch**: `002-business-profiling`
**Created**: 2026-02-02
**Status**: Draft
**Input**: USM EPIC-006 — Профилирование и программа для бизнес/партнёра
**Source**: `docs/02-specification/02-user-story-map.md` (US-011, SS-007)

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Business Partner Profiling (Priority: P1)

As a business partner (investor, HR manager, technology partner), I want to specify my business objective and criteria when I first interact with the bot, so that I receive a curated selection of projects matching my professional interests.

The business partner selects their role during onboarding (EPIC-001 dependency), then proceeds to a profiling flow:

1. Bot asks about the primary business objective: Investment, Hiring, Technology Partnership, or Strategic Partnership
2. Bot asks follow-up questions based on the objective (industry, tech stack, project stage, collaboration format)
3. Partner can also describe their interests in free text (the system extracts the profile)
4. Bot confirms the extracted profile for verification
5. Partner confirms or corrects the profile
6. Profile is saved and used for project recommendations

**Why this priority**: This is the core value proposition for business partners — without profiling, the system cannot generate relevant recommendations. It's the entry point for all subsequent business partner features.

**Independent Test**: Can be fully tested by completing the profiling flow with different business objectives (investor vs HR vs tech partner) and verifying that the profile is correctly saved and confirmed. Delivers value by capturing partner intent.

**Acceptance Scenarios**:

1. **Given** a user has selected "Бизнес/партнёр" role, **When** they start profiling, **Then** bot presents objective options: Инвестиции / Найм / Технология / Партнёрство
2. **Given** partner selected "Инвестиции", **When** profiling continues, **Then** bot asks about preferred project stages (MVP, early traction, scaling), industries, and investment range
3. **Given** partner selected "Найм", **When** profiling continues, **Then** bot asks about roles needed, tech stack preferences, team size, and hiring timeline
4. **Given** partner selected "Технология", **When** profiling continues, **Then** bot asks about problem domain, required capabilities, integration needs
5. **Given** partner selected "Партнёрство", **When** profiling continues, **Then** bot asks about partnership type (pilot, distribution, co-development), industry vertical
6. **Given** partner types free-form text describing interests, **When** text is submitted, **Then** system extracts and displays structured profile for confirmation
7. **Given** bot shows extracted profile, **When** partner confirms, **Then** profile is saved and partner proceeds to recommendations
8. **Given** bot shows extracted profile, **When** partner requests corrections, **Then** bot allows editing specific fields

---

### User Story 2 - Business-Oriented Project Selection (Priority: P2)

As a business partner who completed profiling, I want to receive a personalized selection of projects ranked by business relevance, so that I can efficiently find projects matching my professional objectives.

Based on the saved profile, the system generates a curated list of 5-15 projects:

1. Projects are ranked by match with business criteria (not just thematic match)
2. Each project card shows: name, description, team info, stage, hall/time, relevance score
3. Partner can request more details about any project
4. Partner can save/bookmark interesting projects
5. Partner can request different filtering or re-ranking

**Why this priority**: This delivers the primary value — relevant project discovery. Depends on profiling (P1) being complete. Without this, profiling has no actionable outcome.

**Independent Test**: After profiling as an investor looking for FinTech/NLP projects at MVP stage, verify that the returned selection prioritizes projects matching those criteria and excludes irrelevant ones.

**Acceptance Scenarios**:

1. **Given** partner completed profiling, **When** recommendations are generated, **Then** partner receives 5-15 projects ranked by business relevance
2. **Given** partner is an investor interested in FinTech, **When** viewing recommendations, **Then** FinTech projects appear before unrelated projects
3. **Given** a project card is displayed, **When** partner views it, **Then** they see: name, 2-3 sentence description, team size, project stage, hall/time, relevance explanation
4. **Given** partner wants more details, **When** they tap "Подробнее", **Then** bot shows extended project info (tech stack, business model, team background)
5. **Given** multiple projects are in the same time slot, **When** generating schedule, **Then** system flags the conflict and suggests alternatives
6. **Given** partner doesn't like the selection, **When** they request "Другие проекты", **Then** system shows next batch or asks for refined criteria

---

### User Story 3 - Profile Modification (Priority: P3)

As a business partner, I want to modify my profile after initial setup, so that I can adjust my criteria if my priorities change or I want to explore different projects.

1. Partner can access profile settings at any time via command or menu
2. Partner can change objective, criteria, or add new interests
3. System regenerates recommendations based on updated profile
4. Previous profile is retained for comparison (optional)

**Why this priority**: Enhancement feature — core flow works without this, but improves flexibility and repeat usage.

**Independent Test**: After initial profiling and recommendations, modify the business objective from "Инвестиции" to "Найм" and verify that new recommendations reflect the change.

**Acceptance Scenarios**:

1. **Given** partner has a saved profile, **When** they request profile edit, **Then** current profile is displayed with edit options
2. **Given** partner changes objective from "Инвестиции" to "Найм", **When** they confirm changes, **Then** profile is updated and new recommendations are generated
3. **Given** partner adds additional interests to existing profile, **When** confirmed, **Then** recommendations expand to include new areas

---

### Edge Cases

- **Empty projects database**: If no projects are loaded, system informs partner that recommendations are unavailable and to check back later
- **No matching projects**: If profile is too narrow and no projects match, system suggests broadening criteria and shows closest matches
- **Profiling interruption**: If partner abandons profiling mid-flow, partial data is saved; on return, bot offers to continue or restart
- **Free-text parsing failure**: If system cannot extract profile from free text, it asks clarifying questions or offers structured input
- **Conflicting criteria**: If partner requests contradictory criteria (e.g., "early MVP" + "proven revenue"), system highlights the conflict and asks for priority

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST present business objective options after partner selects their role: Инвестиции, Найм, Технология, Партнёрство
- **FR-002**: System MUST collect objective-specific criteria (stage, industry, stack, collaboration format) based on selected objective
- **FR-003**: System MUST support free-text input for describing business interests
- **FR-004**: System MUST extract structured profile from free-text input and display for confirmation
- **FR-005**: Partner MUST be able to confirm or correct the extracted profile before proceeding
- **FR-006**: System MUST save the confirmed profile linked to the partner's identity
- **FR-007**: System MUST generate project recommendations ranked by business relevance to the profile
- **FR-008**: System MUST display 5-15 projects in the initial recommendation set
- **FR-009**: Each project card MUST include: name, brief description, team info, project stage, hall/time, relevance indicator
- **FR-010**: Partner MUST be able to request detailed information about any project
- **FR-011**: System MUST handle time slot conflicts by flagging overlapping projects
- **FR-012**: Partner MUST be able to modify their profile after initial setup
- **FR-013**: Profile modifications MUST trigger recommendation regeneration
- **FR-014**: Profiling flow MUST complete in ≤2 minutes for structured input path

### Key Entities

- **BusinessProfile**: Represents the partner's business intent and criteria
  - Business objective (investment/hiring/technology/partnership)
  - Industry preferences (list)
  - Technology stack preferences (list)
  - Project stage preferences (list)
  - Collaboration format
  - Free-text description (raw and parsed)
  - Created/updated timestamps

- **ProjectRecommendation**: A ranked project match for a specific profile
  - Reference to project
  - Reference to business profile
  - Relevance score
  - Relevance explanation
  - Viewed/bookmarked status

- **Project**: Demo Day project (exists in system)
  - Name, description, team, stage, track, thematic tags
  - Hall assignment, time slot
  - Business-relevant metadata (business model, team size, funding status)

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Business partners complete profiling in ≤2 minutes (structured path) or ≤3 minutes (free-text path)
- **SC-002**: 80% of business partners confirm their extracted profile without corrections on first attempt
- **SC-003**: Recommended projects have ≥70% thematic overlap with stated business interests
- **SC-004**: Business partners view details of ≥3 projects from their personalized selection
- **SC-005**: Partners can find at least one relevant project within top-5 recommendations in 90% of cases
- **SC-006**: System generates recommendations within 5 seconds of profile confirmation
- **SC-007**: Profile modification and recommendation refresh completes within 10 seconds

---

## Assumptions

- EPIC-001 (Onboarding and role selection) is implemented — partner has already selected "Бизнес/партнёр" role
- Project data is pre-loaded in the system (EPIC-002 dependency) with sufficient metadata for business matching
- ~330 projects available for matching (based on past Demo Day scale)
- AI/LLM capabilities are available for free-text parsing and relevance ranking (Brief v3.0: OpenRouter API)
- Russian language is the primary interface language

---

## Dependencies

- **EPIC-001**: Role selection and onboarding (must be complete)
- **EPIC-002**: Project data loading (projects must exist in system)
- **SS-002**: Project clustering/categorization (provides thematic tags for matching)

---

## Out of Scope

- Q&A question generation for business partners (covered in EPIC-009)
- 1:1 meeting scheduling with project authors (covered in EPIC-010)
- Follow-up package generation (covered in EPIC-015)
- Contact exchange with students (covered in US-020)
- Notifications and reminders (covered in EPIC-007)
