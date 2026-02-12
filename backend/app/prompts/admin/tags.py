"""Prompts for tag generation.

Version: 1.0.0
Last updated: 2026-02-11
"""

import json

# =============================================================================
# Tag Suggestion System Prompt
# =============================================================================

PROJECT_TAG_EXTRACTION_SYSTEM = (
    "Ты AI-ассистент для Demo Day. Проанализируй описание проекта "
    "и определи его тематику.\n"
    "Допустимые теги (с описаниями): {tag_list}\n"
    "Верни JSON строго в формате:\n"
    '{{"tags": ["tag1", "tag2"]}}\n'
    "tags -- только из списка допустимых. Выбери 1-3 наиболее подходящих тега."
)

TAG_SUGGEST_SYSTEM = (
    "Ты AI-ассистент для организатора Demo Day. "
    "Проанализируй названия и описания проектов и предложи 10-20 тегов "
    "для классификации этих проектов по тематикам. "
    "Доступные теги: {available_tags}. "
    "Верни JSON строго в формате:\n"
    '{"tags": ["EdTech", "NLP", "CV", ...]}'
)


# =============================================================================
# User Prompt Builder
# =============================================================================


def build_tag_suggest_prompt(projects: list[dict]) -> str:
    """Build user prompt for tag suggestion.

    Args:
        projects: List of projects with id, title, description

    Returns:
        User prompt string with projects in JSON format

    Example:
        >>> projects = [{"id": "1", "title": "LLM Bot", "description": "AI assistant"}]
        >>> prompt = build_tag_suggest_prompt(projects)
    """
    prompt = f"Проанализируй {len(projects)} проектов и предложи теги.\n\n"
    prompt += "Проекты:\n"
    prompt += json.dumps(projects, ensure_ascii=False, indent=None)
    prompt += "\n\nВерни JSON со списком предложенных тегов."
    return prompt
