"""Prompts for project clustering.

Version: 1.0.0
Last updated: 2026-02-11
"""

import json

# =============================================================================
# Clustering System Prompt
# =============================================================================

CLUSTERING_SYSTEM = """Ты AI-ассистент для организации Demo Day.
Твоя задача — распределить проекты по тематическим залам.

Constraints:
- Каждый проект должен быть ровно в одном зале
- Разница между самым большим и маленьким залом ≤ 5 проектов
- Группируй по тематической близости (NLP, CV, Agents, EdTech, FinTech и т.д.)
- Для каждого зала дай краткое название темы и обоснование (2-3 предложения)
- Названия залов должны быть информативными, например: "NLP и языковые модели", "Автономные агенты"

Верни JSON строго в формате:
{
  "rooms": [
    {
      "name": "Название темы зала",
      "theme_rationale": "Обоснование тематики зала (2-3 предложения)",
      "project_ids": ["id1", "id2", ...]
    }
  ]
}"""


# =============================================================================
# Theme Suggestion System Prompt
# =============================================================================

SUGGEST_THEMES_SYSTEM = """Ты AI-ассистент для организации Demo Day.
Твоя задача — предложить тематики залов на основе анализа проектов.

Проанализируй теги и описания проектов, выяви основные тематические кластеры
(NLP, CV, Agents, EdTech, FinTech, Healthcare, etc).

Constraints:
- Количество тем должно быть ровно равно запрошенному числу залов
- Темы должны быть информативными и отражать содержание проектов (не "Зал 1", "Зал 2")
- Темы должны охватывать все проекты (не создавай слишком узкие темы)
- Учитывай И теги, И descriptions проектов (теги могут быть неполными)

Примеры хороших тем:
- "NLP и языковые модели"
- "Автономные агенты и RAG"
- "Computer Vision и мультимодальные модели"
- "AI в образовании и EdTech"
- "FinTech и предиктивная аналитика"

Верни JSON строго в формате:
{
  "themes": ["Тема зала 1", "Тема зала 2", ...]
}"""


# =============================================================================
# User Prompt Builders
# =============================================================================

def build_clustering_prompt(
    projects: list[dict],
    num_rooms: int,
    feedback: str | None = None,
    room_themes: list[str] | None = None,
) -> str:
    """Build user prompt for clustering.

    Args:
        projects: List of projects with id, title, description, tags
        num_rooms: Number of rooms to create
        feedback: Optional organizer feedback for regeneration
        room_themes: Optional predefined room themes

    Returns:
        User prompt string with projects in JSON format

    Example:
        >>> projects = [{"id": "1", "title": "LLM Bot", "tags": ["NLP"]}]
        >>> prompt = build_clustering_prompt(projects, num_rooms=3)
    """
    prompt = f"Распредели {len(projects)} проектов по {num_rooms} залам.\n\n"

    if room_themes:
        themes = ", ".join(room_themes)
        prompt += f"Тематики залов заданы организатором: {themes}.\n"
        prompt += "Используй эти тематики как названия залов и ориентиры для распределения.\n\n"

    prompt += "Проекты:\n"
    prompt += json.dumps(projects, ensure_ascii=False, indent=None)

    if feedback:
        prompt += f"\n\nФидбэк организатора: {feedback}"

    prompt += "\n\nВерни JSON с распределением."
    return prompt


def build_suggest_themes_prompt(
    projects: list[dict],
    num_rooms: int,
) -> str:
    """Build user prompt for theme suggestion.

    Args:
        projects: List of projects with id, title, description, tags
        num_rooms: Number of themes to suggest

    Returns:
        User prompt string with projects in JSON format

    Example:
        >>> projects = [{"id": "1", "title": "LLM Bot", "tags": ["NLP"]}]
        >>> prompt = build_suggest_themes_prompt(projects, num_rooms=6)
    """
    prompt = f"Предложи {num_rooms} тематик для залов на основе {len(projects)} проектов.\n\n"
    prompt += "Проекты:\n"
    prompt += json.dumps(projects, ensure_ascii=False, indent=None)
    prompt += "\n\nВерни JSON со списком тем."
    return prompt
