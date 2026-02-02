# Quickstart: EPIC-006 — Organizer Coverage Dashboard

## Prerequisites

- Event with approved clustering (EPIC-002)
- Experts assigned to rooms (EPIC-004)
- Experts and projects have tags
- Organizer registered in bot with telegram_user_id in organizer_ids

## Integration Scenarios

### Scenario 1: Organizer checks coverage via bot

1. Organizer sends `/coverage` in Telegram
2. Bot returns summary: each room with expert counts, project counts, coverage status
3. Organizer sees which rooms need attention

**Expected output**:
```
📊 Покрытие залов

✅ Зал «NLP/Agents» — 3 эксп. (подтв.) | 45 проектов
⚠️ Зал «FinTech» — 1 эксп. (подтв.) | 38 проектов
❌ Зал «CV/ML» — 0 эксп. | 52 проектов

Итого: 4/6 подтверждено (67%)

[Зал «NLP/Agents»] [Зал «FinTech»] [Зал «CV/ML»] ...
[🔄 Обновить]
```

### Scenario 2: Organizer drills into a room

1. Organizer clicks room button from coverage summary
2. Bot shows room detail: experts (name, status, tags), project tags, gaps

**Expected output**:
```
🔍 Зал «FinTech» — 38 проектов

Эксперты:
✅ Иванов А.В. (confirmed) — FinTech, ML
⏳ Петрова Е.С. (invited) — Banking, Risk
❌ Сидоров К.Д. (declined) — FinTech

Тематики проектов: FinTech (28), Blockchain (8), InsurTech (5)

⚠️ Непокрытые темы: Blockchain, InsurTech

[⬅️ Назад] [🔄 Обновить]
```

### Scenario 3: Organizer views gaps with recommendations

1. Organizer clicks "gaps" or sends `/gaps` from coverage summary
2. Bot shows all uncovered tags across all rooms with candidate experts

**Expected output**:
```
⚠️ Непокрытые тематики

Зал «FinTech»:
  • Blockchain — 8 проектов
    Кандидаты: Козлов И.А. (Зал «Crypto»), Новикова С.П. (не назначен)
  • InsurTech — 5 проектов
    Кандидаты: нет подходящих экспертов

Зал «CV/ML»:
  • CV — 30 проектов
    Кандидаты: Волков А.Р. (Зал «NLP»), Егоров П.Ю. (не назначен)
```

### Scenario 4: REST API — coverage summary

```
GET /api/v1/coverage
Authorization: Bearer <token>

→ 200 OK
{
  "rooms": [
    {
      "room_id": "...",
      "room_name": "NLP/Agents",
      "project_count": 45,
      "top_tags": ["NLP", "Agents", "LLM", "Chatbots", "RAG"],
      "confirmed": 3,
      "pending": 1,
      "declined": 0,
      "total_assigned": 4,
      "coverage_level": "covered"
    },
    ...
  ],
  "totals": {
    "confirmed": 8,
    "pending": 4,
    "declined": 2,
    "total_needed": 12,
    "coverage_percent": 66.7
  }
}
```

### Scenario 5: REST API — room detail

```
GET /api/v1/coverage/<room_id>
Authorization: Bearer <token>

→ 200 OK
{
  "room_id": "...",
  "room_name": "FinTech",
  "project_count": 38,
  "project_tags": ["FinTech", "Blockchain", "InsurTech", "Banking", "Risk"],
  "experts": [
    {"expert_id": "...", "name": "Иванов А.В.", "status": "confirmed", "match_score": 0.85, "tags": ["FinTech", "ML"], "bot_started": true}
  ],
  "uncovered_tags": ["Blockchain", "InsurTech"],
  "candidates": [
    {"expert_id": "...", "name": "Козлов И.А.", "matching_tags": ["Blockchain"], "current_rooms": ["Crypto"]}
  ]
}
```

### Scenario 6: REST API — all gaps

```
GET /api/v1/coverage/gaps
Authorization: Bearer <token>

→ 200 OK
{
  "total_gaps": 3,
  "gaps": [
    {
      "room_id": "...",
      "room_name": "FinTech",
      "uncovered_tag": "Blockchain",
      "project_count_with_tag": 8,
      "candidates": [...]
    }
  ]
}
```

## Verification Checklist

- [ ] `/coverage` returns all rooms with correct expert/project counts
- [ ] Room drill-down shows experts with statuses and tags
- [ ] Gap analysis correctly identifies uncovered tags
- [ ] Candidate experts are recommended for gaps
- [ ] Non-organizer gets 403 on all endpoints
- [ ] "No approved clustering" handled gracefully
