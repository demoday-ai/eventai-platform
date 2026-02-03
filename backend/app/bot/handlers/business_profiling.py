"""Business partner profiling conversation handler (EPIC-006).

States:
- CHOOSE_OBJECTIVE: Select business goal (Investment/Hiring/Technology/Partnership)
- CHOOSE_CRITERIA: Select industries, stages, tech stack
- FREE_TEXT_INPUT: Optional free-text description
- CONFIRM_PROFILE: Review and confirm extracted profile
- VIEW_RECOMMENDATIONS: Paginated project recommendations
- PROJECT_DETAIL: Single project detail view
"""

import logging
import uuid

from telegram import Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from app.bot.keyboards import (
    confirm_profile_keyboard,
    industries_keyboard,
    objective_keyboard,
    project_card_keyboard,
    recommendations_page_keyboard,
    skip_free_text_keyboard,
    stages_keyboard,
)
from app.database import async_session
from app.models.business_profile import BusinessObjective, OBJECTIVE_DISPLAY
from app.models.role import RoleCode
from app.schemas.profile import BusinessProfileCreate
from app.services import user_service
from app.services import profile_service
from app.services import recommendation_service

logger = logging.getLogger(__name__)

# Conversation states
(
    CHOOSE_OBJECTIVE,
    CHOOSE_INDUSTRIES,
    CHOOSE_STAGES,
    FREE_TEXT_INPUT,
    CONFIRM_PROFILE,
    VIEW_RECOMMENDATIONS,
    PROJECT_DETAIL,
    EDIT_PROFILE,
) = range(8)


async def start_profiling(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point: start profiling for business partner."""
    tg_user = update.effective_user
    telegram_user_id = str(tg_user.id)

    async with async_session() as session:
        user = await user_service.get_user_by_telegram_id(session, telegram_user_id)
        event = await user_service.get_current_event(session)

        if not user or not event:
            await update.message.reply_text("Ошибка. Сначала выберите роль через /start")
            return ConversationHandler.END

        # Check user has business role
        role = await user_service.get_user_role_with_info(session, user.id, event.id)
        if not role or role.code != RoleCode.BUSINESS.value:
            await update.message.reply_text(
                "Эта функция доступна только для бизнес-партнёров.\n"
                "Выберите роль через /start → Бизнес-партнёр"
            )
            return ConversationHandler.END

        # Check for existing profile
        existing = await profile_service.get_profile_by_user_event(
            session, user.id, event.id
        )

        context.user_data["user_id"] = str(user.id)
        context.user_data["event_id"] = str(event.id)

        if existing:
            context.user_data["profile_id"] = str(existing.id)
            # Show existing profile and ask to continue or edit
            summary = profile_service.format_profile_summary(existing)
            await update.message.reply_text(
                f"У вас уже есть профиль:\n\n{summary}\n\n"
                "Что хотите сделать?",
                reply_markup=confirm_profile_keyboard(),
                parse_mode="Markdown",
            )
            return CONFIRM_PROFILE

    # Initialize empty profile data
    context.user_data["profile"] = {
        "objective": None,
        "industries": [],
        "tech_stack": [],
        "project_stages": [],
        "collaboration_format": None,
        "free_text_raw": None,
    }

    await update.message.reply_text(
        "👋 Добро пожаловать в профилирование!\n\n"
        "Выберите вашу основную цель на Demo Day:",
        reply_markup=objective_keyboard(),
    )
    return CHOOSE_OBJECTIVE


async def objective_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle objective selection."""
    query = update.callback_query
    await query.answer()

    _, _, obj_value = query.data.split(":")
    objective = BusinessObjective(obj_value)

    context.user_data["profile"]["objective"] = objective.value
    logger.info("Objective chosen: %s", objective.value)

    await query.edit_message_text(
        f"🎯 Цель: {OBJECTIVE_DISPLAY[objective]}\n\n"
        "Выберите интересующие отрасли (можно несколько):",
        reply_markup=industries_keyboard(context.user_data["profile"].get("industries", [])),
    )
    return CHOOSE_INDUSTRIES


async def industry_toggled(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle industry selection toggle."""
    query = update.callback_query
    await query.answer()

    _, _, industry = query.data.split(":")

    if industry == "done":
        # Move to stages
        await query.edit_message_text(
            "📈 Выберите интересующие стадии проектов:",
            reply_markup=stages_keyboard(context.user_data["profile"].get("project_stages", [])),
        )
        return CHOOSE_STAGES

    # Toggle industry
    industries = context.user_data["profile"].get("industries", [])
    if industry in industries:
        industries.remove(industry)
    else:
        industries.append(industry)
    context.user_data["profile"]["industries"] = industries

    await query.edit_message_text(
        f"🏭 Выбрано отраслей: {len(industries)}\n\n"
        "Выберите интересующие отрасли (можно несколько):",
        reply_markup=industries_keyboard(industries),
    )
    return CHOOSE_INDUSTRIES


async def stage_toggled(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle stage selection toggle."""
    query = update.callback_query
    await query.answer()

    _, _, stage = query.data.split(":")

    if stage == "done":
        # Move to free text
        await query.edit_message_text(
            "💬 Опишите подробнее, что ищете (или пропустите):\n\n"
            "Например: _Ищу NLP-проекты для интеграции в наш продукт, "
            "интересует распознавание намерений на русском языке._",
            reply_markup=skip_free_text_keyboard(),
            parse_mode="Markdown",
        )
        return FREE_TEXT_INPUT

    # Toggle stage
    stages = context.user_data["profile"].get("project_stages", [])
    if stage in stages:
        stages.remove(stage)
    else:
        stages.append(stage)
    context.user_data["profile"]["project_stages"] = stages

    await query.edit_message_text(
        f"📈 Выбрано стадий: {len(stages)}\n\n"
        "Выберите интересующие стадии проектов:",
        reply_markup=stages_keyboard(stages),
    )
    return CHOOSE_STAGES


async def free_text_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle free text input and extract profile with LLM."""
    text = update.message.text
    context.user_data["profile"]["free_text_raw"] = text

    # Try LLM extraction
    try:
        objective_hint = None
        obj_val = context.user_data["profile"].get("objective")
        if obj_val:
            objective_hint = BusinessObjective(obj_val)

        extracted = await profile_service.extract_from_text(text, objective_hint)

        # Merge extracted data with user selections
        profile = context.user_data["profile"]
        if extracted.industries:
            profile["industries"] = list(set(profile.get("industries", []) + extracted.industries))
        if extracted.tech_stack:
            profile["tech_stack"] = extracted.tech_stack
        if extracted.project_stages:
            profile["project_stages"] = list(set(profile.get("project_stages", []) + extracted.project_stages))
        if extracted.collaboration_format:
            profile["collaboration_format"] = extracted.collaboration_format

        context.user_data["extracted"] = extracted.model_dump()

    except RuntimeError:
        # LLM failed — continue with structured data only
        logger.warning("LLM extraction failed, using structured data only")
        await update.message.reply_text(
            "⚠️ AI-анализ временно недоступен. Используем ваши выборы."
        )

    return await show_profile_confirmation(update, context)


async def skip_free_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle skip free text button."""
    query = update.callback_query
    await query.answer()
    return await show_profile_confirmation(update, context, edit_message=True)


async def show_profile_confirmation(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    edit_message: bool = False,
) -> int:
    """Show profile summary for confirmation."""
    profile = context.user_data["profile"]

    # Format summary
    obj = BusinessObjective(profile["objective"])
    lines = [
        "📋 **Ваш профиль:**\n",
        f"🎯 Цель: {OBJECTIVE_DISPLAY[obj]}",
    ]

    if profile.get("industries"):
        lines.append(f"🏭 Отрасли: {', '.join(profile['industries'])}")
    if profile.get("tech_stack"):
        lines.append(f"💻 Технологии: {', '.join(profile['tech_stack'])}")
    if profile.get("project_stages"):
        stages_display = {
            "idea": "Идея", "mvp": "MVP", "early_traction": "Ранняя тяга",
            "scaling": "Масштабирование", "mature": "Зрелый",
        }
        stages = [stages_display.get(s, s) for s in profile["project_stages"]]
        lines.append(f"📈 Стадии: {', '.join(stages)}")
    if profile.get("collaboration_format"):
        lines.append(f"🤝 Формат: {profile['collaboration_format']}")

    lines.append("\nВсё верно?")
    text = "\n".join(lines)

    if edit_message:
        query = update.callback_query
        await query.edit_message_text(
            text,
            reply_markup=confirm_profile_keyboard(),
            parse_mode="Markdown",
        )
    else:
        await update.message.reply_text(
            text,
            reply_markup=confirm_profile_keyboard(),
            parse_mode="Markdown",
        )

    return CONFIRM_PROFILE


async def profile_confirmed(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle profile confirmation."""
    query = update.callback_query
    await query.answer()

    _, _, action = query.data.split(":")

    if action == "restart":
        # Clear and restart
        context.user_data["profile"] = {
            "objective": None,
            "industries": [],
            "tech_stack": [],
            "project_stages": [],
            "collaboration_format": None,
            "free_text_raw": None,
        }
        await query.edit_message_text(
            "🔄 Начнём заново.\n\nВыберите вашу основную цель:",
            reply_markup=objective_keyboard(),
        )
        return CHOOSE_OBJECTIVE

    if action == "edit":
        await query.edit_message_text(
            "✎ Что хотите изменить?\n\nВыберите цель:",
            reply_markup=objective_keyboard(),
        )
        return CHOOSE_OBJECTIVE

    # action == "yes" — save profile
    profile_data = context.user_data.get("profile")

    # T040: Handle interrupted profiling — recover gracefully
    if not profile_data or not profile_data.get("objective"):
        await query.edit_message_text(
            "⚠️ Данные профиля не найдены.\n\n"
            "Начнём профилирование заново.",
            reply_markup=objective_keyboard(),
        )
        context.user_data["profile"] = {
            "objective": None,
            "industries": [],
            "tech_stack": [],
            "project_stages": [],
            "collaboration_format": None,
            "free_text_raw": None,
        }
        return CHOOSE_OBJECTIVE

    user_id = uuid.UUID(context.user_data["user_id"])
    event_id = uuid.UUID(context.user_data["event_id"])

    async with async_session() as session:
        create_data = BusinessProfileCreate(
            user_id=user_id,
            event_id=event_id,
            objective=BusinessObjective(profile_data["objective"]),
            industries=profile_data.get("industries"),
            tech_stack=profile_data.get("tech_stack"),
            project_stages=profile_data.get("project_stages"),
            collaboration_format=profile_data.get("collaboration_format"),
            free_text_raw=profile_data.get("free_text_raw"),
        )

        saved_profile = await profile_service.create_or_update_profile(
            session,
            create_data,
            free_text_parsed=context.user_data.get("extracted"),
        )
        context.user_data["profile_id"] = str(saved_profile.id)

        await query.edit_message_text("✓ Профиль сохранён!\n\n🔍 Подбираю проекты...")

        # Generate recommendations
        try:
            recs = await recommendation_service.generate_recommendations(
                session, saved_profile, max_results=15
            )
            logger.info("Generated %d recommendations", len(recs))

            # T038: Handle empty projects database
            if not recs:
                await query.message.reply_text(
                    "😕 К сожалению, не нашлось проектов по вашим критериям.\n\n"
                    "💡 Попробуйте:\n"
                    "• Расширить выбор отраслей\n"
                    "• Выбрать больше стадий проектов\n"
                    "• Изменить формулировку интересов",
                    reply_markup=confirm_profile_keyboard(),
                )
                return CONFIRM_PROFILE

            # Show first page
            return await show_recommendations(update, context, session, page=1)

        except Exception as e:
            logger.error("Recommendation generation failed: %s", e)
            await query.message.reply_text(
                "⚠️ Не удалось подобрать проекты. Попробуйте позже."
            )
            return ConversationHandler.END


async def show_recommendations(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    session=None,
    page: int = 1,
) -> int:
    """Show paginated recommendations."""
    profile_id = uuid.UUID(context.user_data["profile_id"])
    page_size = 5

    close_session = False
    if session is None:
        session = async_session()
        close_session = True

    try:
        recs, total = await recommendation_service.get_recommendations(
            session, profile_id, page=page, page_size=page_size
        )

        if not recs:
            msg = update.callback_query.message if update.callback_query else update.message
            await msg.reply_text("Нет рекомендаций. Попробуйте изменить профиль.")
            return CONFIRM_PROFILE

        # Load projects for display
        for rec in recs:
            if not hasattr(rec, "project") or rec.project is None:
                rec_with_proj = await recommendation_service.get_recommendation_with_project(
                    session, rec.id
                )
                if rec_with_proj:
                    rec.project = rec_with_proj.project

        total_pages = (total + page_size - 1) // page_size
        context.user_data["rec_page"] = page

        # Format recommendations
        lines = [f"📊 **Рекомендации** (стр. {page}/{total_pages}):\n"]
        for rec in recs:
            if rec.project:
                score_pct = rec.relevance_score
                lines.append(f"• {rec.project.title[:40]} — {score_pct}%")

        text = "\n".join(lines)

        keyboard = recommendations_page_keyboard(page, total_pages, recs)

        if update.callback_query:
            await update.callback_query.edit_message_text(
                text, reply_markup=keyboard, parse_mode="Markdown"
            )
        else:
            msg = update.callback_query.message if update.callback_query else update.message
            await msg.reply_text(text, reply_markup=keyboard, parse_mode="Markdown")

        return VIEW_RECOMMENDATIONS

    finally:
        if close_session:
            await session.close()


async def recommendation_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle recommendation list actions."""
    query = update.callback_query
    await query.answer()

    parts = query.data.split(":")
    action = parts[2] if len(parts) > 2 else parts[1]

    if action == "noop":
        return VIEW_RECOMMENDATIONS

    if action.startswith("page:"):
        page = int(parts[3])
        async with async_session() as session:
            return await show_recommendations(update, context, session, page=page)

    if action == "refresh":
        # Regenerate recommendations
        profile_id = uuid.UUID(context.user_data["profile_id"])
        async with async_session() as session:
            profile = await profile_service.get_profile_by_id(session, profile_id)
            if profile:
                await query.edit_message_text("🔄 Обновляю рекомендации...")
                await recommendation_service.generate_recommendations(
                    session, profile, max_results=15
                )
                return await show_recommendations(update, context, session, page=1)
        return VIEW_RECOMMENDATIONS

    if action == "edit":
        # Go to edit profile
        await query.edit_message_text(
            "✎ Редактирование профиля.\n\nВыберите новую цель:",
            reply_markup=objective_keyboard(),
        )
        return CHOOSE_OBJECTIVE

    return VIEW_RECOMMENDATIONS


async def project_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle project selection from recommendations."""
    query = update.callback_query
    await query.answer()

    # Parse recommendation ID (first 8 chars)
    parts = query.data.split(":")
    rec_id_short = parts[2]

    if rec_id_short == "back":
        async with async_session() as session:
            page = context.user_data.get("rec_page", 1)
            return await show_recommendations(update, context, session, page=page)

    # Find full recommendation by prefix
    profile_id = uuid.UUID(context.user_data["profile_id"])

    async with async_session() as session:
        recs, _ = await recommendation_service.get_recommendations(
            session, profile_id, page=1, page_size=100
        )
        rec = None
        for r in recs:
            if str(r.id).startswith(rec_id_short):
                rec = r
                break

        if not rec:
            await query.edit_message_text("Проект не найден.")
            return VIEW_RECOMMENDATIONS

        # Load full project
        rec = await recommendation_service.get_recommendation_with_project(session, rec.id)
        if not rec or not rec.project:
            await query.edit_message_text("Проект не найден.")
            return VIEW_RECOMMENDATIONS

        # Mark as viewed
        await recommendation_service.mark_viewed(session, rec.id)

        context.user_data["current_rec_id"] = str(rec.id)

        # Format project card
        project = rec.project
        tags = [pt.tag.name for pt in project.tags if pt.tag][:5]

        lines = [
            f"**{project.title}**\n",
            f"👤 {project.author}",
            f"\n📝 {project.description[:400]}{'...' if len(project.description) > 400 else ''}",
        ]
        if tags:
            lines.append(f"\n🏷 {', '.join(tags)}")
        if rec.relevance_explanation:
            lines.append(f"\n💡 _{rec.relevance_explanation}_")
        lines.append(f"\n📊 Релевантность: {rec.relevance_score}%")

        text = "\n".join(lines)

        await query.edit_message_text(
            text,
            reply_markup=project_card_keyboard(str(rec.id), rec.is_bookmarked),
            parse_mode="Markdown",
        )
        return PROJECT_DETAIL


async def bookmark_toggled(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Toggle bookmark for current project."""
    query = update.callback_query
    await query.answer()

    parts = query.data.split(":")
    rec_id_short = parts[2]

    async with async_session() as session:
        # Find full ID
        profile_id = uuid.UUID(context.user_data["profile_id"])
        recs, _ = await recommendation_service.get_recommendations(
            session, profile_id, page=1, page_size=100
        )
        rec_id = None
        for r in recs:
            if str(r.id).startswith(rec_id_short):
                rec_id = r.id
                break

        if rec_id:
            rec = await recommendation_service.toggle_bookmark(session, rec_id)
            if rec:
                status = "добавлен в избранное ⭐" if rec.is_bookmarked else "убран из избранного"
                await query.answer(f"Проект {status}")

                # Refresh card
                rec = await recommendation_service.get_recommendation_with_project(session, rec_id)
                project = rec.project

                lines = [
                    f"**{project.title}**\n",
                    f"👤 {project.author}",
                    f"\n📝 {project.description[:400]}{'...' if len(project.description) > 400 else ''}",
                ]
                if rec.relevance_explanation:
                    lines.append(f"\n💡 _{rec.relevance_explanation}_")
                lines.append(f"\n📊 Релевантность: {rec.relevance_score}%")

                await query.edit_message_text(
                    "\n".join(lines),
                    reply_markup=project_card_keyboard(str(rec.id), rec.is_bookmarked),
                    parse_mode="Markdown",
                )

    return PROJECT_DETAIL


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel profiling."""
    await update.message.reply_text("Профилирование отменено.")
    return ConversationHandler.END


def get_business_profiling_handler() -> ConversationHandler:
    """Create and return the business profiling conversation handler."""
    return ConversationHandler(
        entry_points=[
            CommandHandler("profile", start_profiling),
            CommandHandler("profiling", start_profiling),
        ],
        states={
            CHOOSE_OBJECTIVE: [
                CallbackQueryHandler(objective_chosen, pattern=r"^bp:obj:"),
            ],
            CHOOSE_INDUSTRIES: [
                CallbackQueryHandler(industry_toggled, pattern=r"^bp:ind:"),
            ],
            CHOOSE_STAGES: [
                CallbackQueryHandler(stage_toggled, pattern=r"^bp:stg:"),
            ],
            FREE_TEXT_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, free_text_received),
                CallbackQueryHandler(skip_free_text, pattern=r"^bp:text:skip$"),
            ],
            CONFIRM_PROFILE: [
                CallbackQueryHandler(profile_confirmed, pattern=r"^bp:confirm:"),
            ],
            VIEW_RECOMMENDATIONS: [
                CallbackQueryHandler(project_selected, pattern=r"^bp:proj:"),
                CallbackQueryHandler(recommendation_action, pattern=r"^bp:rec:"),
                CallbackQueryHandler(recommendation_action, pattern=r"^bp:noop$"),
            ],
            PROJECT_DETAIL: [
                CallbackQueryHandler(bookmark_toggled, pattern=r"^bp:bm:"),
                CallbackQueryHandler(project_selected, pattern=r"^bp:proj:back$"),
            ],
            EDIT_PROFILE: [
                CallbackQueryHandler(objective_chosen, pattern=r"^bp:obj:"),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        name="business_profiling",
        persistent=False,
    )
