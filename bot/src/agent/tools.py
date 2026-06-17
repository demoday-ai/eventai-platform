"""Tool implementations for the EventAI PydanticAI agent.

Eight tools available to the LLM agent during VIEW_PROGRAM state:

- show_project      -- карточка проекта: описание, стек, метрики из артефактов, автор.
                       Принимает номер (#1) или название. Поиск среди рекомендаций.
- show_profile      -- текущий профиль гостя: теги, цели, summary. Без параметров.
- compare_projects  -- сравнение 2-5 проектов. LLM генерирует матрицу по критериям
                       (тематика/стек/применимость для гостей, стадия/бизнес-модель для бизнеса).
- generate_questions -- 3-5 вопросов для Q&A автору. Персонализированы под роль
                       (студент -> технические, HR -> найм/команда/пилот).
- update_status     -- бизнес-пайплайн: interested/contacted/meeting_scheduled/rejected/in_progress.
                       Только role=business. Создает BusinessFollowup в БД.
- filter_projects   -- фильтр рекомендаций по тегу или технологии (case-insensitive).
- get_summary       -- итоги: для гостей follow-up пакет (контакты + шаблон),
                       для бизнеса pipeline (статусы + шаблоны обращений).
- github_drilldown  -- GitHub-репозиторий через gh CLI (live).
                       summary: полный анализ (stars, commits, health, red flags).
                       file: содержимое файла (до 3000 символов).
                       tree: структура файлов (до 100 записей).
                       commits: последние 10 коммитов.
                       contributors: топ-10 контрибьюторов с процентами.
"""

import asyncio
import logging

from pydantic_ai import Agent, RunContext
from sqlalchemy import delete, select, func

from src.agent.agent import AgentDeps
from src.models.business_followup import BusinessFollowup
from src.models.project import Project
from src.models.recommendation import Recommendation

logger = logging.getLogger(__name__)

# Human-readable RU labels for business-pipeline statuses (displayed to the user;
# the DB stores the English keys).
STATUS_RU = {
    "interested": "интересует",
    "contacted": "связались",
    "meeting_scheduled": "встреча запланирована",
    "rejected": "отклонён",
    "in_progress": "в работе",
}


def register_tools(agent: Agent[AgentDeps, str]) -> None:
    """Register all 8 tools on the given agent instance."""

    @agent.tool
    async def show_project(
        ctx: RunContext[AgentDeps], project_identifier: str
    ) -> str:
        """Показать карточку проекта: описание, стек, метрики из артефактов (PPTX/PDF/README), автор.

        Args:
            project_identifier: номер (#1, "1") или название проекта ("ChatLaw").
                Поиск среди рекомендаций пользователя.
        Returns:
            Форматированная карточка с данными из БД + parsed_content (артефакты).
        """
        deps = ctx.deps

        # Try rank first
        rec = None
        try:
            rank = int(project_identifier.strip().lstrip("#"))
            rec = _find_recommendation(deps.recommendations, rank)
        except ValueError:
            pass

        # Fallback: search by name among recommended projects
        if not rec:
            name_lower = project_identifier.strip().lower()
            project_ids = [r.project_id for r in deps.recommendations]
            if project_ids:
                result = await deps.db.execute(
                    select(Project).where(
                        Project.id.in_(project_ids),
                        func.lower(Project.title).contains(name_lower),
                    )
                )
                matched = result.scalars().first()
                if matched:
                    rec = next(
                        (r for r in deps.recommendations if r.project_id == matched.id),
                        None,
                    )

        if not rec:
            return f"Проект '{project_identifier}' не найден в рекомендациях."

        result = await deps.db.execute(
            select(Project).where(Project.id == rec.project_id)
        )
        project = result.scalar_one_or_none()
        if not project:
            return f"Проект '{project_identifier}' не найден."

        # Remember the last shown project so the next turn can resolve "этот
        # проект" and so questions:/contact: buttons find it after returning to
        # view_program (program.py persists this back into FSM state).
        ctx.deps.current_project_rank = rec.rank
        ctx.deps.current_project_title = project.title
        return _format_project_card(project, rec)

    @agent.tool
    async def show_profile(ctx: RunContext[AgentDeps]) -> str:
        """Показать текущий профиль гостя: выбранные теги, цели, NL-summary, бизнес-поля."""
        deps = ctx.deps
        if not deps.profile:
            return "Профиль не создан. Используйте /rebuild для персонализации."

        from src.agent.agent import _format_profile

        return _format_profile(deps.profile)

    @agent.tool
    async def compare_projects(
        ctx: RunContext[AgentDeps], project_ranks: list[int]
    ) -> str:
        """Сравнить 2-5 проектов через LLM-матрицу.

        Критерии зависят от роли: для гостей (тематика, стек, применимость),
        для бизнеса (стадия, команда, бизнес-модель, готовность к пилоту).
        Использует отдельный LLM-вызов для генерации матрицы.

        Args:
            project_ranks: список номеров проектов из рекомендаций, например [1, 3].
        """
        deps = ctx.deps
        if len(project_ranks) < 2:
            return "Для сравнения нужно минимум 2 проекта."

        ranks = project_ranks[:5]  # cap at 5

        projects: list[Project] = []
        for rank in ranks:
            rec = _find_recommendation(deps.recommendations, rank)
            if not rec:
                return f"Проект {rank} не найден в рекомендациях."
            result = await deps.db.execute(
                select(Project).where(Project.id == rec.project_id)
            )
            project = result.scalar_one_or_none()
            if project:
                projects.append(project)

        if len(projects) < 2:
            return "Недостаточно проектов для сравнения."

        from src.prompts.qa import build_comparison_matrix_prompt

        is_business = deps.user.role_code == "business"
        criteria = _get_default_criteria(is_business)
        projects_text = "\n".join(
            _build_project_context(p) for p in projects
        )

        system_prompt, user_prompt = build_comparison_matrix_prompt(
            projects_text, criteria
        )

        from src.schemas.tools import ComparisonResult

        try:
            result = await asyncio.wait_for(
                deps.platform.structured_completion(
                    [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    ComparisonResult,
                ),
                timeout=25.0,
            )
            return _format_matrix(result.matrix, criteria)
        except Exception as e:
            logger.error("Compare projects failed: %s", e, exc_info=True)
            return "Не удалось сгенерировать сравнение. Попробуйте позже."

    @agent.tool
    async def generate_questions(
        ctx: RunContext[AgentDeps], project_rank: int
    ) -> str:
        """Подготовить 3-5 вопросов для Q&A автору проекта.

        Вопросы персонализированы: студент -> технические/архитектурные,
        HR/бизнес -> найм, команда, пилот, масштабирование.
        Использует данные из артефактов (презентация, GitHub) для контекста.

        Args:
            project_rank: номер проекта из рекомендаций.
        """
        deps = ctx.deps
        rec = _find_recommendation(deps.recommendations, project_rank)
        if not rec:
            return f"Проект {project_rank} не найден в рекомендациях."

        result = await deps.db.execute(
            select(Project).where(Project.id == rec.project_id)
        )
        project = result.scalar_one_or_none()
        if not project:
            return "Проект не найден."

        from src.prompts.qa import build_business_qa_prompt, build_guest_qa_prompt

        # Enrich description with artifact context
        enriched_desc = _build_project_context(project, max_desc=500)

        if deps.user.role_code == "business":
            system_prompt, user_prompt = build_business_qa_prompt(
                objective=(
                    deps.profile.objective if deps.profile else "technology"
                ),
                industries=(
                    ", ".join(deps.profile.business_objectives or [])
                    if deps.profile
                    else ""
                ),
                tech_stack=", ".join(project.tech_stack or []),
                project_title=project.title,
                project_description=enriched_desc,
                project_tech_stack=", ".join(project.tech_stack or []),
            )
        else:
            system_prompt, user_prompt = build_guest_qa_prompt(
                subtype=deps.user.subrole or "other",
                interests=(
                    ", ".join(deps.profile.selected_tags or [])
                    if deps.profile
                    else ""
                ),
                project_title=project.title,
                project_description=enriched_desc,
                project_tech_stack=", ".join(project.tech_stack or []),
            )

        from src.schemas.tools import QnAResult

        try:
            result = await asyncio.wait_for(
                deps.platform.structured_completion(
                    [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    QnAResult,
                ),
                timeout=20.0,
            )
            questions = result.questions

            lines = [f"Вопросы для проекта {project_rank} ({project.title}):\n"]
            for i, q in enumerate(questions, 1):
                lines.append(f"{i}. {q}")
            return "\n".join(lines)
        except Exception as e:
            logger.error("Generate questions failed: %s", e, exc_info=True)
            return "Не удалось сгенерировать вопросы. Попробуйте позже."

    @agent.tool
    async def update_status(
        ctx: RunContext[AgentDeps], project_rank: int, status: str
    ) -> str:
        """Обновить статус проекта в бизнес-пайплайне (BusinessFollowup в БД).

        Только для role=business. Создает запись если нет, обновляет если есть.

        Args:
            project_rank: номер проекта из рекомендаций.
            status: один из interested, contacted, meeting_scheduled, rejected, in_progress.
        """
        deps = ctx.deps
        if deps.user.role_code != "business":
            return "Эта функция доступна только бизнес-пользователям."

        VALID = {"interested", "contacted", "meeting_scheduled", "rejected", "in_progress"}
        if status not in VALID:
            return f"Допустимые статусы: {', '.join(sorted(VALID))}"

        rec = _find_recommendation(deps.recommendations, project_rank)
        if not rec:
            return f"Проект {project_rank} не найден."

        try:
            result = await deps.db.execute(
                select(BusinessFollowup).where(
                    BusinessFollowup.user_id == deps.user.id,
                    BusinessFollowup.event_id == deps.event.id,
                    BusinessFollowup.project_id == rec.project_id,
                )
            )
            followup = result.scalar_one_or_none()
            if followup:
                old = followup.status
                followup.status = status
                await deps.db.flush()
                return (
                    f"Статус проекта {project_rank} изменён: "
                    f"{STATUS_RU.get(old, old)} -> {STATUS_RU.get(status, status)}"
                )
            else:
                new = BusinessFollowup(
                    user_id=deps.user.id,
                    event_id=deps.event.id,
                    project_id=rec.project_id,
                    status=status,
                )
                deps.db.add(new)
                await deps.db.flush()
                return f"Проект {project_rank} добавлен в пайплайн: {STATUS_RU.get(status, status)}"
        except Exception as e:
            logger.error("update_status failed: %s", e, exc_info=True)
            await deps.db.rollback()
            return "Не получилось обновить статус, попробуйте ещё раз."

    @agent.tool
    async def filter_projects(ctx: RunContext[AgentDeps], tag: str) -> str:
        """Отфильтровать рекомендованные проекты по тегу или технологии (case-insensitive).

        Ищет совпадение в project.tags и project.tech_stack.

        Args:
            tag: тег или технология для фильтрации, например "NLP" или "PyTorch".
        """
        deps = ctx.deps
        if not deps.recommendations:
            return "Нет рекомендаций. Используйте /rebuild."

        tag_lower = tag.strip().lower()
        matched: list[tuple[Recommendation, Project]] = []

        # Load all recommended projects in one query
        project_ids = [r.project_id for r in deps.recommendations]
        result = await deps.db.execute(
            select(Project).where(Project.id.in_(project_ids))
        )
        projects = {p.id: p for p in result.scalars().all()}

        for rec in deps.recommendations:
            project = projects.get(rec.project_id)
            if not project:
                continue
            project_tags = [t.lower() for t in (project.tags or [])]
            project_stack = [t.lower() for t in (project.tech_stack or [])]
            if tag_lower in project_tags or tag_lower in project_stack:
                matched.append((rec, project))

        if not matched:
            return f"Нет проектов с тегом '{tag}' в ваших рекомендациях."

        lines = [f"Проекты с тегом '{tag}' ({len(matched)}):\n"]
        for rec, project in matched:
            lines.append(f"{rec.rank} {project.title}")
            tags_str = ", ".join(project.tags[:3]) if project.tags else ""
            if tags_str:
                lines.append(f"   {tags_str}")
        return "\n".join(lines)

    @agent.tool
    async def get_summary(ctx: RunContext[AgentDeps]) -> str:
        """Итоговая сводка по рекомендованным проектам.

        Гости: follow-up пакет (ранжированный список + Telegram-контакты + шаблон сообщения).
        Бизнес: pipeline (статусы проектов + контакты + шаблоны первого/повторного обращения).
        """
        deps = ctx.deps
        if deps.user.role_code == "business":
            return await _get_pipeline(deps)
        return await _get_followup(deps)

    @agent.tool
    async def github_drilldown(
        ctx: RunContext[AgentDeps],
        project_identifier: str,
        query_type: str,
        file_path: str | None = None,
    ) -> str:
        """Получить данные из GitHub-репозитория проекта (live через gh CLI subprocess).

        Все вызовы идут через `gh api` (GitHub REST API), без клонирования репо.
        Требует установленный gh CLI и опционально GITHUB_TOKEN для rate limit.

        Args:
            project_identifier: номер (#1) или название проекта.
            query_type:
                "summary" - полный анализ: stars, forks, commits, contributors,
                    languages, has_tests/ci/docker, health_score, red_flags.
                    Внутри ~6 параллельных gh api вызовов.
                "file" - содержимое одного файла (до 3000 символов, base64 decode).
                    Нужен file_path.
                "tree" - структура файлов (до 100 записей, recursive).
                    file_path опционально для поддиректории.
                "commits" - последние 10 коммитов (sha, date, author, message).
                "contributors" - топ-10 контрибьюторов с количеством и процентом коммитов.
            file_path: путь к файлу/директории (для query_type file/tree).
        """
        deps = ctx.deps

        VALID_TYPES = {"summary", "file", "tree", "commits", "contributors"}
        if query_type not in VALID_TYPES:
            return f"Допустимые типы: {', '.join(sorted(VALID_TYPES))}"

        if query_type == "file" and not file_path:
            return "Для просмотра файла укажите file_path."

        # Resolve project
        rec = None
        try:
            rank = int(project_identifier.strip().lstrip("#"))
            rec = _find_recommendation(deps.recommendations, rank)
        except ValueError:
            pass

        if not rec:
            # name search
            name_lower = project_identifier.strip().lower()
            project_ids = [r.project_id for r in deps.recommendations]
            if project_ids:
                result = await deps.db.execute(
                    select(Project).where(
                        Project.id.in_(project_ids),
                        func.lower(Project.title).contains(name_lower),
                    )
                )
                matched = result.scalars().first()
                if matched:
                    rec = next(
                        (r for r in deps.recommendations if r.project_id == matched.id),
                        None,
                    )

        if not rec:
            return f"Проект '{project_identifier}' не найден в рекомендациях."

        result = await deps.db.execute(
            select(Project).where(Project.id == rec.project_id)
        )
        project = result.scalar_one_or_none()
        if not project or not project.github_url:
            return f"У проекта {project.title if project else '?'} нет GitHub-репозитория."

        from src.services.github_analyzer import (
            fetch_commits,
            fetch_contributors,
            fetch_file,
            fetch_tree,
            parse_github_url,
        )

        parsed = parse_github_url(project.github_url)
        if not parsed:
            return f"Невалидный GitHub URL: {project.github_url}"

        owner, repo = parsed
        token = ""
        try:
            from src.core.config import settings
            token = settings.github_token
        except Exception:
            pass

        if query_type == "summary":
            # Live analysis via gh API
            from src.services.github_analyzer import analyze_repo

            try:
                gh = await asyncio.wait_for(
                    analyze_repo(owner, repo, token), timeout=20.0,
                )
            except asyncio.TimeoutError:
                return "GitHub не ответил в течение 20 секунд."
            except Exception as e:
                logger.error("GitHub analyze_repo error: %s", e, exc_info=True)
                return "Не удалось проанализировать репозиторий."

            if gh.get("error"):
                return gh["error"]

            lines = [f"GitHub: {gh.get('full_name', f'{owner}/{repo}')}\n"]
            lines.append(f"Звезды: {gh.get('stars', 0)} | Форки: {gh.get('forks_count', 0)}")
            lines.append(
                f"Коммитов: {gh.get('total_commits', '?')} | "
                f"Контрибьюторов: {gh.get('contributors_count', '?')}"
            )
            if gh.get("primary_language"):
                lines.append(f"Язык: {gh['primary_language']}")
            lines.append(f"Последний пуш: {gh.get('days_since_last_push', '?')} дней назад")
            lines.append(f"Возраст: {gh.get('repo_age_days', '?')} дней")
            lines.append(
                f"Тесты: {'есть' if gh.get('has_tests') else 'нет'} | "
                f"CI: {'есть' if gh.get('has_ci') else 'нет'} | "
                f"Docker: {'есть' if gh.get('has_docker') else 'нет'}"
            )
            if gh.get("license"):
                lines.append(f"Лицензия: {gh['license']}")
            lines.append(f"Health score: {gh.get('health_score', '?')}/100")

            if gh.get("contributors"):
                lines.append("\nКонтрибьюторы:")
                for c in gh["contributors"][:5]:
                    lines.append(f"  {c['login']}: {c['contributions']} ({c['percentage']}%)")

            flags = gh.get("red_flags", [])
            if flags:
                lines.append("\nRed flags:")
                for f in flags:
                    lines.append(f"  [{f.get('severity', '?')}] {f.get('description', '?')}")

            return "\n".join(lines)

        # Real-time drill-down via gh CLI
        try:
            if query_type == "file":
                return await asyncio.wait_for(
                    fetch_file(owner, repo, file_path, token), timeout=15.0,
                )
            elif query_type == "tree":
                return await asyncio.wait_for(
                    fetch_tree(owner, repo, token, file_path or ""), timeout=15.0,
                )
            elif query_type == "commits":
                return await asyncio.wait_for(
                    fetch_commits(owner, repo, token), timeout=15.0,
                )
            elif query_type == "contributors":
                return await asyncio.wait_for(
                    fetch_contributors(owner, repo, token), timeout=15.0,
                )
        except asyncio.TimeoutError:
            return "GitHub не ответил в течение 15 секунд."
        except Exception as e:
            logger.error("GitHub drilldown error: %s", e)
            return f"Ошибка при получении данных: {e}"

        return "Неизвестная ошибка"

    @agent.tool
    async def update_program(
        ctx: RunContext[AgentDeps],
        remove: list[int] | None = None,
        add: list[int] | None = None,
        exclude: list[str] | None = None,
    ) -> str:
        """Быстро поправить программу БЕЗ пересборки (мгновенно).

        Вызывай когда пользователь хочет убрать/добавить конкретный проект или
        исключить тему ("убери таможню", "добавь проект 5", "не интересно X").

        Args:
            remove: номера проектов из программы, которые убрать.
            add: номера проектов из программы (из блока "если успеете"),
                которые поднять в основу.
            exclude: темы/теги/направления, которые гостю НЕ интересны
                (запоминаются в профиль; матчащие проекты убираются).
        """
        deps = ctx.deps
        if deps.profile is None:
            return "Профиль не создан, программу пока нельзя править."
        remove = remove or []
        add = add or []
        exclude = exclude or []
        changed: list[str] = []

        try:
            if exclude:
                terms = [t.strip() for t in exclude if t.strip()]
                if terms:
                    note = "Не интересует: " + ", ".join(terms)
                    deps.profile.nl_summary = (
                        (deps.profile.nl_summary or "") + "\n" + note
                    ).strip()
                    ids = [r.project_id for r in deps.recommendations]
                    drop_pids: set = set()
                    if ids:
                        # Room/track name matters too ("AI Security" is the zal, not a tag).
                        rooms = await _project_rooms(deps.db, ids)
                        res = await deps.db.execute(
                            select(Project).where(Project.id.in_(ids))
                        )
                        low = [t.lower() for t in terms]
                        for p in res.scalars().all():
                            hay = " ".join(
                                [p.title or ""]
                                + (p.tags or [])
                                + [p.description or "", rooms.get(p.id, "")]
                            ).lower()
                            if any(t in hay for t in low):
                                drop_pids.add(p.id)
                    if drop_pids:
                        await deps.db.execute(
                            delete(Recommendation).where(
                                Recommendation.guest_profile_id == deps.profile.id,
                                Recommendation.project_id.in_(drop_pids),
                            )
                        )
                    changed.append("исключил темы: " + ", ".join(terms))

            if remove:
                rm_ranks = set(remove)
                rm_pids = [
                    r.project_id for r in deps.recommendations if r.rank in rm_ranks
                ]
                if rm_pids:
                    await deps.db.execute(
                        delete(Recommendation).where(
                            Recommendation.guest_profile_id == deps.profile.id,
                            Recommendation.project_id.in_(rm_pids),
                        )
                    )
                    changed.append(f"убрал из программы: {len(rm_pids)}")

            if add:
                add_ranks = set(add)
                promoted = 0
                for r in deps.recommendations:
                    if r.rank in add_ranks and r.category != "must_visit":
                        r.category = "must_visit"
                        promoted += 1
                if promoted:
                    changed.append(f"поднял в основу: {promoted}")

            if not changed:
                return "Нечего менять: укажите номер проекта или тему."

            await deps.db.flush()
            await _reload_recs(deps)
        except Exception as e:
            logger.error("update_program failed: %s", e, exc_info=True)
            await deps.db.rollback()
            return "Не получилось обновить программу, попробуйте ещё раз."

        from src.bot.routers.program import format_program

        text, _ = await format_program(
            deps.recommendations, deps.db, header="Обновлённая программа:"
        )
        return "Готово (" + "; ".join(changed) + ").\n\n" + text

    @agent.tool
    async def rebuild_program(ctx: RunContext[AgentDeps], note: str) -> str:
        """Пересобрать программу под изменившиеся интересы (1 LLM-вызов).

        Вызывай когда пользователь меняет/расширяет интересы
        ("больше про RAG", "интересует ещё биотех"). Профиль сохраняется,
        не сбрасывается. Для простого убрать/исключить используй update_program.

        Args:
            note: что добавить к интересам гостя (одна фраза).
        """
        deps = ctx.deps
        if deps.profile is None:
            return "Профиль не создан, пересборка недоступна."
        if note and note.strip():
            deps.profile.nl_summary = (
                (deps.profile.nl_summary or "") + "\n" + note.strip()
            ).strip()
            await deps.db.flush()

        interests = deps.profile.selected_tags or []
        keywords = deps.profile.keywords or []
        parts: list[str] = []
        if interests:
            parts.append("Интересы: " + ", ".join(interests))
        if keywords:
            parts.append("Цели: " + ", ".join(keywords))
        if deps.profile.nl_summary:
            parts.append(deps.profile.nl_summary)
        profile_text = "\n".join(parts) or (deps.profile.raw_text or "общие интересы")

        from src.services.retriever import generate_recommendations

        try:
            recs = await generate_recommendations(
                db=deps.db,
                platform=deps.platform,
                profile_id=deps.profile.id,
                event_id=deps.event.id,
                profile_text=profile_text,
                selected_tags=interests,
            )
        except Exception as e:
            logger.error("rebuild_program failed: %s", e, exc_info=True)
            return "Не удалось пересобрать программу, попробуйте позже."

        if not recs:
            return "Под новый запрос подходящих проектов не нашлось."

        deps.recommendations = recs
        from src.bot.routers.program import format_program

        text, _ = await format_program(recs, deps.db, header="Пересобрал программу:")
        return text

    @agent.tool
    async def search_catalog(ctx: RunContext[AgentDeps], query: str) -> str:
        """Найти проекты по ВСЕМУ каталогу Demo Day (~330), а не только в подборке гостя.

        Вызывай на "что есть про X", "покажи все проекты про Y", "есть ли проекты про Z",
        "хочу посмотреть шире", "весь каталог". Это исследование за пределами программы.

        Args:
            query: тема, технология или запрос для поиска по каталогу.
        """
        deps = ctx.deps
        from src.services.retriever import _pgvector_search

        try:
            emb = await deps.platform.embedding(query)
            rows = await _pgvector_search(deps.db, emb, deps.event.id, limit=8)
        except Exception as e:
            logger.error("search_catalog failed: %s", e, exc_info=True)
            return "Не удалось выполнить поиск по каталогу, попробуйте позже."

        if not rows:
            return f"По запросу «{query}» в каталоге ничего не нашлось."

        rec_pids = {r.project_id for r in deps.recommendations}
        lines = [f"Из общего каталога Demo Day по запросу «{query}»:"]
        for r in rows:
            tags = ", ".join((r.get("tags") or [])[:3])
            mark = " (уже в вашей программе)" if r["project_id"] in rec_pids else ""
            line = f"- {r['title']}"
            if tags:
                line += f" — {tags}"
            line += mark
            lines.append(line)
        lines.append(
            "\nЭто из всего каталога (~330 проектов), а не только ваша подборка."
        )
        return "\n".join(lines)

    @agent.tool
    async def show_program(ctx: RunContext[AgentDeps]) -> str:
        """Показать персональную программу гостя ЦЕЛИКОМ, как она есть в базе.

        Вызывай на "покажи мою программу", "что у меня в программе", "покажи
        целиком", "моя программа". Возвращает программу дословно - отдай её
        пользователю БЕЗ изменений и НЕ пересказывай номера/время своими словами.
        """
        deps = ctx.deps
        if not deps.recommendations:
            return "Программа пуста. Опишите интересы или используйте /rebuild."
        from src.bot.routers.program import format_program

        text, _ = await format_program(
            deps.recommendations, deps.db, header="Ваша программа:"
        )
        return text

    @agent.tool
    async def add_project(ctx: RunContext[AgentDeps], name: str) -> str:
        """Добавить КОНКРЕТНЫЙ проект из каталога в программу по названию (без пересборки).

        Вызывай когда гость просит добавить названный проект, которого нет в
        подборке ("добавь Deepfake detection", "добавь проект X в программу").
        Для проектов, которые уже в программе (в т.ч. в 'если успеете'),
        используй update_program(add=[номер]).

        Args:
            name: название проекта (или узнаваемая часть) из каталога.
        """
        deps = ctx.deps
        if deps.profile is None:
            return "Профиль не создан, добавить нельзя."
        name_low = name.strip().lower()
        if not name_low:
            return "Укажите название проекта."

        res = await deps.db.execute(
            select(Project)
            .where(
                Project.event_id == deps.event.id,
                func.lower(Project.title).contains(name_low),
            )
            .limit(1)
        )
        project = res.scalars().first()
        if not project:
            # Fallback: token-overlap match so "chat law" finds "ChatLaw",
            # "AutoDS система" finds "AutoDS", etc. (substring LIKE misses these).
            project = await _fuzzy_find_project(deps.db, deps.event.id, name)
        if not project:
            return f"Не нашёл в каталоге проект «{name}». Уточните название."
        if any(r.project_id == project.id for r in deps.recommendations):
            return f"«{project.title}» уже в вашей программе."

        from src.models.schedule_slot import ScheduleSlot

        try:
            slot_res = await deps.db.execute(
                select(ScheduleSlot.id).where(ScheduleSlot.project_id == project.id).limit(1)
            )
            slot_id = slot_res.scalar_one_or_none()
            max_rank = max((r.rank for r in deps.recommendations), default=0)
            deps.db.add(
                Recommendation(
                    guest_profile_id=deps.profile.id,
                    project_id=project.id,
                    relevance_score=100.0,
                    category="must_visit",
                    rank=max_rank + 1,
                    slot_id=slot_id,
                )
            )
            await deps.db.flush()
            await _reload_recs(deps)
        except Exception as e:
            logger.error("add_project failed: %s", e, exc_info=True)
            await deps.db.rollback()
            return "Не получилось добавить проект, попробуйте ещё раз."

        from src.bot.routers.program import format_program

        text, _ = await format_program(
            deps.recommendations, deps.db, header="Добавил в программу:"
        )
        return text


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _reload_recs(deps: AgentDeps) -> None:
    """Reload the profile's recommendations from DB and renumber them 1..N by
    display order (must_visit -> if_time, chronological). Keeps the shown number
    equal to the project's position, gap-free after edits. Persists the new ranks
    and refreshes deps.recommendations for in-run consistency."""
    from src.services.retriever import _load_schedule_slots, _renumber_by_display

    result = await deps.db.execute(
        select(Recommendation)
        .where(Recommendation.guest_profile_id == deps.profile.id)
        .order_by(Recommendation.rank)
    )
    recs = list(result.scalars().all())
    slots = await _load_schedule_slots(deps.db, deps.event.id)
    _renumber_by_display(recs, slots)
    await deps.db.flush()
    deps.recommendations = recs


def _norm_tokens(s: str) -> set:
    import re

    return set(re.findall(r"\w+", (s or "").lower()))


async def _fuzzy_find_project(db, event_id, name: str):
    """Best token-overlap match of `name` against catalog titles (event-scoped).

    Handles spacing/case the substring LIKE misses ("chat law" -> "ChatLaw").
    Also matches when the query's collapsed form is a substring of the collapsed
    title. Returns the Project or None if nothing clears a 0.5 overlap threshold.
    """
    import re

    want = _norm_tokens(name)
    want_collapsed = re.sub(r"\W+", "", (name or "").lower())
    if not want and not want_collapsed:
        return None
    rows = (
        await db.execute(select(Project).where(Project.event_id == event_id))
    ).scalars().all()
    best, best_score = None, 0.0
    for p in rows:
        title_collapsed = re.sub(r"\W+", "", (p.title or "").lower())
        if want_collapsed and want_collapsed in title_collapsed:
            return p
        toks = _norm_tokens(p.title)
        if not toks or not want:
            continue
        score = len(want & toks) / min(len(want), len(toks))
        if score > best_score:
            best, best_score = p, score
    return best if best_score >= 0.5 else None


async def _project_rooms(db, project_ids: list) -> dict:
    """Map project_id -> room/track name (for exclude-by-track matching)."""
    if not project_ids:
        return {}
    from src.models.room import Room
    from src.models.schedule_slot import ScheduleSlot

    res = await db.execute(
        select(ScheduleSlot.project_id, Room.name)
        .join(Room, ScheduleSlot.room_id == Room.id)
        .where(ScheduleSlot.project_id.in_(project_ids))
    )
    return {pid: (name or "") for pid, name in res.all()}


def _find_recommendation(
    recs: list[Recommendation], rank: int
) -> Recommendation | None:
    """Find recommendation by rank number."""
    for r in recs:
        if r.rank == rank:
            return r
    return None


def _get_default_criteria(is_business: bool) -> list[str]:
    """Return default comparison criteria based on user role."""
    if is_business:
        return [
            "Стадия проекта",
            "Размер команды",
            "Технический стек",
            "Бизнес-модель",
            "Готовность к пилоту",
        ]
    return [
        "Тематика",
        "Технологии",
        "Практическая применимость",
        "Инновационность",
        "Зрелость проекта",
    ]


def _build_project_context(project: Project, max_desc: int = 200) -> str:
    """Build rich text context including artifact data."""
    parts = [f"- {project.title}: {project.description[:max_desc]}"]
    if project.tech_stack:
        parts.append(f"  Стек: {', '.join(project.tech_stack)}")

    pc = project.parsed_content if isinstance(project.parsed_content, dict) else None
    if pc:
        if pc.get("problem"):
            parts.append(f"  Проблема: {pc['problem']}")
        if pc.get("solution"):
            parts.append(f"  Решение: {pc['solution']}")
        if pc.get("key_metrics"):
            parts.append(f"  Метрики: {', '.join(pc['key_metrics'])}")
        if pc.get("novelty"):
            parts.append(f"  Новизна: {pc['novelty']}")
        if pc.get("risks"):
            parts.append(f"  Риски: {pc['risks']}")
        if pc.get("production_readiness"):
            parts.append(f"  Готовность: {pc['production_readiness']}")
    return "\n".join(parts)


def _format_project_card(project: Project, rec: Recommendation) -> str:
    """Format a single project into a readable card."""
    lines = [
        f"{rec.rank} {project.title}\n",
        project.description[:300],
    ]
    if project.tags:
        lines.append(f"\nТеги: {', '.join(project.tags)}")
    if project.tech_stack:
        lines.append(f"Стек: {', '.join(project.tech_stack)}")

    if project.parsed_content and isinstance(project.parsed_content, dict):
        pc = project.parsed_content
        if pc.get("problem"):
            lines.append(f"\nПроблема: {pc['problem']}")
        if pc.get("solution"):
            lines.append(f"Решение: {pc['solution']}")
        if pc.get("audience"):
            lines.append(f"Аудитория: {pc['audience']}")
        if pc.get("novelty"):
            lines.append(f"Новизна: {pc['novelty']}")
        if pc.get("key_metrics"):
            lines.append(f"Метрики: {', '.join(pc['key_metrics'])}")
        if pc.get("production_readiness"):
            lines.append(f"Готовность: {pc['production_readiness']}")
        if pc.get("risks"):
            lines.append(f"Риски: {pc['risks']}")
        red_flags = pc.get("red_flags")
        if red_flags:
            flags_text = "; ".join(
                f"{f['description']} ({f['severity']})"
                for f in red_flags
                if isinstance(f, dict)
            )
            if flags_text:
                lines.append(f"Red flags: {flags_text}")

    if project.author:
        lines.append(f"\nАвтор: {project.author}")
    return "\n".join(lines)


def _format_matrix(matrix: dict, criteria: list[str]) -> str:
    """Format comparison matrix dict into readable text."""
    if not matrix:
        return "Не удалось сгенерировать матрицу."

    lines = ["Матрица сравнения:\n"]
    for criterion in criteria:
        lines.append(f"*{criterion}:*")
        for project_name, scores in matrix.items():
            value = scores.get(criterion, "-")
            lines.append(f"  {project_name}: {value}")
        lines.append("")
    return "\n".join(lines)


def _outreach_ask(objective: str | None) -> str:
    """One-line ask personalised by the guest's objective (see prompts/qa.py)."""
    return {
        "investment": "Интересует обсуждение раунда и условий инвестиций.",
        "hiring": "Интересует ваша команда — рассматриваем открытые позиции.",
        "partnership": "Интересует обсуждение пилота и партнёрства.",
        "technology": "Интересует обсуждение пилота и технической интеграции.",
    }.get(objective or "", "Интересует обсуждение возможного сотрудничества.")


async def _get_followup(deps: AgentDeps) -> str:
    """Build follow-up package for guest users."""
    if not deps.recommendations:
        return "Нет рекомендаций. Используйте /rebuild."

    lines = ["Follow-up пакет:\n"]
    first_title: str | None = None
    for rec in deps.recommendations[:10]:
        result = await deps.db.execute(
            select(Project).where(Project.id == rec.project_id)
        )
        project = result.scalar_one_or_none()
        if project:
            if first_title is None:
                first_title = project.title
            contact = (
                f" | {project.telegram_contact}" if project.telegram_contact else ""
            )
            lines.append(f"{rec.rank} {project.title}{contact}")

    title = first_title or "ваш проект"
    lines.append("\nШаблон для связи:")
    lines.append(f"Здравствуйте! Видел(а) ваш проект «{title}» на Demo Day.")
    lines.append("Интересует возможность пообщаться и обменяться опытом.")
    return "\n".join(lines)


async def _get_pipeline(deps: AgentDeps) -> str:
    """Build business pipeline summary."""
    result = await deps.db.execute(
        select(BusinessFollowup).where(
            BusinessFollowup.user_id == deps.user.id,
            BusinessFollowup.event_id == deps.event.id,
        )
    )
    followups = result.scalars().all()

    if not followups:
        return "Пайплайн пуст. Сначала получите рекомендации."

    stats: dict[str, int] = {}
    for f in followups:
        stats[f.status] = stats.get(f.status, 0) + 1

    lines = ["Business Pipeline:\n"]
    for status, count in stats.items():
        lines.append(f"  {STATUS_RU.get(status, status)}: {count}")
    lines.append("")

    rep_title: str | None = None
    for f in followups[:10]:
        result = await deps.db.execute(
            select(Project).where(Project.id == f.project_id)
        )
        project = result.scalar_one_or_none()
        if project:
            if rep_title is None:
                rep_title = project.title
            lines.append(f"[{STATUS_RU.get(f.status, f.status)}] {project.title}")
            if project.telegram_contact:
                lines.append(f"  Контакт: {project.telegram_contact}")
            if f.notes:
                lines.append(f"  {f.notes[:50]}")

    company = deps.profile.company if deps.profile and deps.profile.company else None
    objective = deps.profile.objective if deps.profile else None
    rep = rep_title or "ваш проект"
    greet = f"Здравствуйте! Представляю компанию {company}." if company else "Здравствуйте!"

    lines.append("\nШаблоны для связи:")
    lines.append("")
    lines.append("Первое обращение:")
    lines.append(greet)
    lines.append(f"Видели ваш проект «{rep}» на Demo Day.")
    lines.append(_outreach_ask(objective))
    lines.append("Удобно будет созвониться на этой неделе?")
    lines.append("")
    lines.append("Повторное обращение:")
    lines.append(f"Добрый день! Мы общались на Demo Day по проекту «{rep}».")
    lines.append("Хотел(а) бы уточнить детали и обсудить следующий шаг.")

    return "\n".join(lines)
