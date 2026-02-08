from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from app.models.role import RoleCode


def role_keyboard() -> InlineKeyboardMarkup:
    """Four-button role selection: Student, Applicant, Business, Other."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎓 Студент", callback_data="role:guest:student"),
            InlineKeyboardButton("📚 Абитуриент", callback_data="role:guest:applicant"),
        ],
        [
            InlineKeyboardButton("💼 Бизнес", callback_data=f"role:{RoleCode.BUSINESS.value}"),
            InlineKeyboardButton("👤 Другое", callback_data="role:guest:other"),
        ],
    ])


def confirm_nl_profile_keyboard(prefix: str = "nlconf") -> InlineKeyboardMarkup:
    """Confirm or re-enter NL profile.

    Args:
        prefix: Callback data prefix. Use "onb_nlconf" for onboarding, "reb_nlconf" for rebuild.
    """
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✓ Всё верно", callback_data=f"{prefix}:yes")],
        [InlineKeyboardButton("✎ Ввести заново", callback_data=f"{prefix}:retry")],
    ])


# --- Guest program keyboards ---


def program_recommendation_keyboard(
    recommendations: list[dict],
    has_if_time: bool = False,
) -> InlineKeyboardMarkup:
    """Inline buttons for project details from recommendation list (no pagination)."""
    buttons = []
    for rec in recommendations:
        label = f"#{rec['rank']} {rec['title'][:35]}"
        pid_short = rec["project_id"][:12]
        buttons.append([InlineKeyboardButton(label, callback_data=f"pdetail:{pid_short}")])

    if has_if_time:
        buttons.append([InlineKeyboardButton("Ещё рекомендации", callback_data="prof:show_if_time")])
    buttons.append([
        InlineKeyboardButton("👤 Мой профиль", callback_data="prof:show_profile"),
        InlineKeyboardButton("Обновить профиль", callback_data="profile:update"),
    ])
    return InlineKeyboardMarkup(buttons)


def check_readiness_keyboard() -> InlineKeyboardMarkup:
    """Inline button to check if recommendation generation is ready."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Проверить готовность", callback_data="prof:check_ready")],
    ])


def retry_generation_keyboard() -> InlineKeyboardMarkup:
    """Inline button to retry failed recommendation generation."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Попробовать заново", callback_data="prof:retry_gen")],
        [InlineKeyboardButton("Изменить профиль", callback_data="profile:update")],
    ])
