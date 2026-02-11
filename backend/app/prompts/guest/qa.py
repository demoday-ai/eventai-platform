"""Prompts for Q&A assistance and project comparison.

Version: 1.0.0
Last updated: 2026-02-11
"""

from app.models.business_profile import BusinessObjective

# =============================================================================
# Q&A Generation Prompts
# =============================================================================

GUEST_QA_SYSTEM = """Ты — помощник для гостей Demo Day. Генерируй вопросы на русском языке.
Вопросы должны быть конкретными, содержательными и учитывать профиль гостя.
Формат ответа: JSON объект с полем "questions" — массив строк."""


BUSINESS_QA_SYSTEM = """Ты — помощник для бизнес-партнёров Demo Day. Генерируй вопросы на русском языке.
Вопросы должны быть бизнес-ориентированными и учитывать цель партнёра.
Формат ответа: JSON объект с полем "questions" — массив строк."""


def build_guest_qa_prompt(
    subtype_desc: str,
    interests: str,
    project_title: str,
    project_description: str,
    project_tech_stack: str,
) -> tuple[str, str]:
    """Build LLM prompt for guest questions.

    Args:
        subtype_desc: Guest subtype description (e.g., "Абитуриент", "AI-практик")
        interests: Guest interests formatted as string (tags + keywords)
        project_title: Project title
        project_description: Project description (truncated to 500 chars)
        project_tech_stack: Project tech stack

    Returns:
        Tuple of (system_prompt, user_prompt)

    Example:
        >>> sys_prompt, user_prompt = build_guest_qa_prompt(
        ...     "AI-практик",
        ...     "\\nИнтересы: NLP, Agents",
        ...     "LLM-чат-бот",
        ...     "Виртуальный ассистент...",
        ...     "Python, FastAPI"
        ... )
    """
    user_prompt = f"""Сгенерируй 3-5 вопросов для гостя, который хочет посетить проект.

Профиль гостя:
- Тип: {subtype_desc}{interests}

Проект:
- Название: {project_title}
- Описание: {project_description}
- Технологии: {project_tech_stack}

Правила генерации:
- Абитуриент: фокус на обучении, команде, технологиях для изучения, карьерном пути
- AI-практик: фокус на архитектуре, подходах, метриках, воспроизводимости, инновациях
- Гость: общие вопросы про ценность проекта, применимость, планы развития

Ответь JSON: {{"questions": ["вопрос1", "вопрос2", ...]}}"""

    return GUEST_QA_SYSTEM, user_prompt


def build_business_qa_prompt(
    objective: BusinessObjective,
    industries: list[str],
    tech_stack: list[str],
    project_title: str,
    project_description: str,
    project_tech_stack: str,
) -> tuple[str, str]:
    """Build LLM prompt for business partner questions.

    Args:
        objective: Business objective (investment, hiring, technology, partnership)
        industries: Partner's industry focus
        tech_stack: Partner's tech stack focus
        project_title: Project title
        project_description: Project description (truncated to 500 chars)
        project_tech_stack: Project tech stack

    Returns:
        Tuple of (system_prompt, user_prompt)
    """
    objective_map = {
        BusinessObjective.INVESTMENT: "Инвестор",
        BusinessObjective.HIRING: "HR / нанимающий менеджер",
        BusinessObjective.TECHNOLOGY: "Технологический партнёр",
        BusinessObjective.PARTNERSHIP: "Бизнес-партнёр",
    }
    objective_desc = objective_map.get(objective, "Партнёр")

    industries_str = ", ".join(industries) if industries else "Не указано"
    tech_str = ", ".join(tech_stack) if tech_stack else "Не указано"

    user_prompt = f"""Сгенерируй 3-5 бизнес-вопросов для партнёра, оценивающего проект.

Профиль партнёра:
- Цель: {objective_desc}
- Отрасли: {industries_str}
- Технологический фокус: {tech_str}

Проект:
- Название: {project_title}
- Описание: {project_description}
- Технологии: {project_tech_stack}

Правила генерации по цели:
- Инвестор: unit-экономика, рынок, команда, стадия, раунд, метрики
- HR: стек, опыт команды, готовность к работе, интересы, мотивация
- Технологический партнёр: интеграция, API, масштабирование, лицензия
- Бизнес-партнёр: бизнес-модель, готовность к пилоту, условия сотрудничества

Ответь JSON: {{"questions": ["вопрос1", "вопрос2", ...]}}"""

    return BUSINESS_QA_SYSTEM, user_prompt


# =============================================================================
# Comparison Matrix Prompts
# =============================================================================

COMPARISON_MATRIX_SYSTEM = """Ты — аналитик Demo Day. Создай матрицу сравнения проектов.
Оцени каждый проект по каждому критерию кратко (1-3 слова или оценка).
Формат ответа: JSON объект с полем "matrix" — словарь {project_title: {criterion: value}}."""


def build_comparison_matrix_prompt(
    project_list: str,
    criteria: list[str],
) -> tuple[str, str]:
    """Build LLM prompt for project comparison matrix.

    Args:
        project_list: Formatted list of projects with descriptions
        criteria: List of comparison criteria

    Returns:
        Tuple of (system_prompt, user_prompt)

    Example:
        >>> project_list = "1. LLM-чат-бот\\n   Описание: ...\\n2. Fraud Detection\\n   Описание: ..."
        >>> criteria = ["Стадия", "Стек", "Готовность к внедрению"]
        >>> sys_prompt, user_prompt = build_comparison_matrix_prompt(project_list, criteria)
    """
    criteria_list = ", ".join(criteria)

    user_prompt = f"""Сравни проекты по критериям.

Проекты:
{project_list}

Критерии: {criteria_list}

Для каждого проекта укажи значение по каждому критерию.
Ответь JSON: {{"matrix": {{"Название проекта": {{"Критерий1": "значение", ...}}, ...}}}}"""

    return COMPARISON_MATRIX_SYSTEM, user_prompt
