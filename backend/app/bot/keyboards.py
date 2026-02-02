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


# --- Clustering keyboards ---


def confirm_replace_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Да, заменить", callback_data="replace:yes")],
            [InlineKeyboardButton("Нет, отмена", callback_data="replace:no")],
        ]
    )


def room_count_keyboard(project_count: int) -> InlineKeyboardMarkup:
    buttons = []
    row = []
    for n in [4, 5, 6, 7, 8]:
        row.append(InlineKeyboardButton(f"{n} залов", callback_data=f"rooms:{n}"))
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(buttons)


def rooms_overview_keyboard(rooms_info: list) -> InlineKeyboardMarkup:
    """rooms_info: list of (Room, project_count) tuples."""
    buttons = []
    for room, count in rooms_info:
        label = f"Зал {room.display_order + 1}: {room.name[:20]} ({count})"
        buttons.append([InlineKeyboardButton(label, callback_data=f"room:{room.id}")])

    buttons.append([
        InlineKeyboardButton("Перегенерировать", callback_data="action:regenerate"),
        InlineKeyboardButton("Утвердить", callback_data="action:approve"),
    ])
    return InlineKeyboardMarkup(buttons)


def room_detail_keyboard(
    room_id, page: int, total_pages: int, project_count: int
) -> InlineKeyboardMarkup:
    buttons = []

    # Pagination row
    if total_pages > 1:
        nav = []
        if page > 0:
            nav.append(InlineKeyboardButton("◀", callback_data=f"page:{room_id}:{page - 1}"))
        nav.append(InlineKeyboardButton(f"{page + 1}/{total_pages}", callback_data="noop"))
        if page < total_pages - 1:
            nav.append(InlineKeyboardButton("▶", callback_data=f"page:{room_id}:{page + 1}"))
        buttons.append(nav)

    # Action row
    buttons.append([
        InlineKeyboardButton("Перенести проект", callback_data="action:move"),
        InlineKeyboardButton("Назад", callback_data="action:back"),
    ])
    return InlineKeyboardMarkup(buttons)


def project_list_keyboard(projects: list, page: int = 0, page_size: int = 8) -> InlineKeyboardMarkup:
    """Paginated project list with pick buttons."""
    start = page * page_size
    page_projects = projects[start:start + page_size]
    total_pages = (len(projects) + page_size - 1) // page_size

    buttons = []
    for p in page_projects:
        label = p.title[:40]
        buttons.append([InlineKeyboardButton(label, callback_data=f"pick:{p.id}")])

    # Pagination
    if total_pages > 1:
        nav = []
        if page > 0:
            nav.append(InlineKeyboardButton("◀", callback_data=f"ppage:{page - 1}"))
        if page < total_pages - 1:
            nav.append(InlineKeyboardButton("▶", callback_data=f"ppage:{page + 1}"))
        buttons.append(nav)

    buttons.append([InlineKeyboardButton("Назад", callback_data="action:back")])
    return InlineKeyboardMarkup(buttons)


def target_room_keyboard(rooms_info: list) -> InlineKeyboardMarkup:
    """rooms_info: list of (Room, count) tuples."""
    buttons = []
    for room, count in rooms_info:
        label = f"{room.name[:25]} ({count})"
        buttons.append([InlineKeyboardButton(label, callback_data=f"target:{room.id}")])
    buttons.append([InlineKeyboardButton("Отмена", callback_data="action:back")])
    return InlineKeyboardMarkup(buttons)


def approve_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Утвердить", callback_data="approve:yes")],
            [InlineKeyboardButton("Назад", callback_data="approve:no")],
        ]
    )
