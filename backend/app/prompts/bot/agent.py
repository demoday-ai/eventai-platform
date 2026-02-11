"""Prompts for bot agent mode (VIEW_PROGRAM state).

Version: 1.0.0
Last updated: 2026-02-11
"""

# =============================================================================
# Agent Mode System Prompt
# =============================================================================


def build_agent_system_prompt(
    is_business: bool,
    profile_info: str,
    recs_summary: str,
    num_recommendations: int,
) -> str:
    """Build system prompt for agent mode in VIEW_PROGRAM state.

    Args:
        is_business: True if user is business partner, False if guest
        profile_info: Formatted user profile information
        recs_summary: Formatted summary of recommendations (projects list)
        num_recommendations: Total number of recommended projects

    Returns:
        Complete system prompt for agent with:
        - Role definition
        - Available tools
        - Rules for tool usage
        - User profile
        - Recommendations summary

    Example:
        >>> prompt = build_agent_system_prompt(
        ...     is_business=False,
        ...     profile_info="Интересы: NLP, Agents\\nЦели: Найти проекты AI-ассистентов",
        ...     recs_summary="1. LLM-чат-бот\\n2. AI-агент для скоринга\\n...",
        ...     num_recommendations=12
        ... )
    """
    if is_business:
        role_tools = "- get_pipeline — показать бизнес-пайплайн (статусы проектов)\n"
    else:
        role_tools = "- get_followup — follow-up пакет (итоги, контакты, next steps)\n"

    return (
        "Ты — AI-куратор Demo Day. Пользователь получил персональную программу проектов.\n"
        "Отвечай кратко, по делу, на русском. Без эмодзи.\n\n"
        f"РОЛЬ ПОЛЬЗОВАТЕЛЯ: {'бизнес-партнёр' if is_business else 'гость'}\n\n"
        "ИНСТРУМЕНТЫ (tools):\n"
        "- show_project — показать детали ОДНОГО проекта по номеру\n"
        "- show_profile — показать профиль пользователя\n"
        "- compare_projects — сравнить 2-5 проектов (генерирует матрицу сравнения)\n"
        "- generate_questions — подготовить вопросы для Q&A к проекту\n"
        f"{role_tools}"
        "- rebuild_profile — перезапустить профилирование\n\n"
        "ПРАВИЛА:\n"
        "- Для сравнения проектов ВСЕГДА вызывай compare_projects, НЕ пиши текстом\n"
        "- show_project — ТОЛЬКО для одного проекта, НЕ для сравнения\n"
        "- Если пользователь хочет изменить интересы — вызови rebuild_profile\n"
        "- Для простых вопросов о проектах отвечай текстом, используя данные из РЕКОМЕНДАЦИЙ\n"
        "- Помогай планировать маршрут по залам\n\n"
        f"ПРОФИЛЬ:\n{profile_info}\n\n"
        f"РЕКОМЕНДАЦИИ ({num_recommendations} проектов):\n{recs_summary}"
    )
