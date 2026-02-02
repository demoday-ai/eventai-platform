from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from app.models.role import ROLE_DISPLAY_NAMES, RoleCode
from app.models.user import GUEST_SUBTYPE_DISPLAY, GuestSubtype


def role_keyboard(is_organizer: bool = False) -> InlineKeyboardMarkup:
    roles = [
        (RoleCode.STUDENT, ROLE_DISPLAY_NAMES[RoleCode.STUDENT]),
        (RoleCode.EXPERT, ROLE_DISPLAY_NAMES[RoleCode.EXPERT]),
        (RoleCode.GUEST, ROLE_DISPLAY_NAMES[RoleCode.GUEST]),
        (RoleCode.BUSINESS, ROLE_DISPLAY_NAMES[RoleCode.BUSINESS]),
    ]
    if is_organizer:
        roles.insert(0, (RoleCode.ORGANIZER, ROLE_DISPLAY_NAMES[RoleCode.ORGANIZER]))

    buttons = [
        [InlineKeyboardButton(name, callback_data=f"role:{code.value}")]
        for code, name in roles
    ]
    return InlineKeyboardMarkup(buttons)


def guest_subtype_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(display, callback_data=f"subtype:{st.value}")]
        for st, display in GUEST_SUBTYPE_DISPLAY.items()
    ]
    return InlineKeyboardMarkup(buttons)


def confirm_change_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Да, сменить роль", callback_data="change:yes")],
            [InlineKeyboardButton("Нет, оставить", callback_data="change:no")],
        ]
    )
