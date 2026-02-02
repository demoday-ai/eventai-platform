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


# --- Expert assignment keyboards ---


def expert_management_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Запустить матчинг", callback_data="exp:match")],
        [InlineKeyboardButton("Загрузить экспертов", callback_data="exp:upload")],
        [InlineKeyboardButton("Покрытие", callback_data="exp:coverage")],
        [InlineKeyboardButton("Приглашения", callback_data="exp:invites")],
        [InlineKeyboardButton("Эскалации", callback_data="exp:escalations")],
    ])


def matching_result_rooms(rooms_info: list) -> InlineKeyboardMarkup:
    """rooms_info: list of dicts with room_id, room_name, expert_count."""
    buttons = []
    for i, r in enumerate(rooms_info):
        label = f"Зал {i + 1}: {r['room_name'][:20]} ({r['expert_count']})"
        buttons.append([InlineKeyboardButton(label, callback_data=f"mroom:{r['room_id'][:8]}")])

    buttons.append([
        InlineKeyboardButton("Перезапустить", callback_data="exp:rematch"),
        InlineKeyboardButton("Утвердить", callback_data="exp:approve_match"),
    ])
    return InlineKeyboardMarkup(buttons)


def room_expert_detail_keyboard(
    experts: list, room_id: str, page: int = 0, page_size: int = 8
) -> InlineKeyboardMarkup:
    """Show experts in a room with move buttons."""
    start = page * page_size
    page_experts = experts[start:start + page_size]
    total_pages = max(1, (len(experts) + page_size - 1) // page_size)

    buttons = []
    for exp in page_experts:
        score = exp.get("match_score", 0)
        manual = " (ручн.)" if exp.get("is_manual") else ""
        label = f"{exp['name'][:25]} [{score:.1f}]{manual}"
        buttons.append([InlineKeyboardButton(label, callback_data=f"mexp:{exp['expert_id'][:8]}")])

    if total_pages > 1:
        nav = []
        if page > 0:
            nav.append(InlineKeyboardButton("<<", callback_data=f"mpage:{room_id[:8]}:{page - 1}"))
        nav.append(InlineKeyboardButton(f"{page + 1}/{total_pages}", callback_data="noop"))
        if page < total_pages - 1:
            nav.append(InlineKeyboardButton(">>", callback_data=f"mpage:{room_id[:8]}:{page + 1}"))
        buttons.append(nav)

    buttons.append([InlineKeyboardButton("Назад к залам", callback_data="exp:back_rooms")])
    return InlineKeyboardMarkup(buttons)


def move_target_room_keyboard(rooms_info: list, current_room_id: str) -> InlineKeyboardMarkup:
    """List rooms to move expert to (excluding current)."""
    buttons = []
    for i, r in enumerate(rooms_info):
        if r["room_id"] == current_room_id:
            continue
        label = f"Зал {i + 1}: {r['room_name'][:25]} ({r['expert_count']})"
        buttons.append([InlineKeyboardButton(label, callback_data=f"mtarget:{r['room_id'][:8]}")])
    buttons.append([InlineKeyboardButton("Отмена", callback_data="exp:back_detail")])
    return InlineKeyboardMarkup(buttons)


def approve_matching_confirm() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Да, утвердить", callback_data="exp:confirm_approve")],
        [InlineKeyboardButton("Нет, назад", callback_data="exp:back_rooms")],
    ])


def invite_preview_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Подтвердить рассылку", callback_data="exp:confirm_invite")],
        [InlineKeyboardButton("Отмена", callback_data="exp:menu")],
    ])


def expert_invite_actions() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Иду", callback_data="einv:confirm")],
        [InlineKeyboardButton("Хочу другую комнату", callback_data="einv:reassign")],
        [InlineKeyboardButton("Не смогу", callback_data="einv:decline")],
    ])


def alternative_rooms_keyboard(rooms: list) -> InlineKeyboardMarkup:
    """rooms: list of (room_id, name, project_count)."""
    buttons = []
    for room_id, name, count in rooms:
        label = f"{name[:25]} ({count} проектов)"
        buttons.append([InlineKeyboardButton(label, callback_data=f"eroom:{str(room_id)[:8]}")])
    buttons.append([InlineKeyboardButton("Отмена", callback_data="einv:cancel_reassign")])
    return InlineKeyboardMarkup(buttons)


def expert_confirmed_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Сменить комнату", callback_data="einv:change_room")],
    ])


def coverage_dashboard_rooms(rooms_data: list) -> InlineKeyboardMarkup:
    """rooms_data: list of RoomCoverageSummary dicts."""
    indicators = {"covered": "🟢", "partial": "🟡", "uncovered": "🔴"}
    buttons = []
    for r in rooms_data:
        ind = indicators.get(r.get("coverage_level", "uncovered"), "🔴")
        label = f"{ind} {r['room_name'][:20]} ({r['confirmed']}/{r['needed']})"
        buttons.append([InlineKeyboardButton(label, callback_data=f"croom:{str(r['room_id'])[:8]}")])
    buttons.append([InlineKeyboardButton("Назад", callback_data="exp:menu")])
    return InlineKeyboardMarkup(buttons)


def coverage_room_detail_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Назад к покрытию", callback_data="exp:coverage")],
    ])


def escalation_list_keyboard(escalations: list) -> InlineKeyboardMarkup:
    """escalations: list of EscalationResponse-like dicts."""
    buttons = []
    for esc in escalations[:10]:
        label = f"{esc['type'][:15]}: {esc['expert_name'][:20]}"
        buttons.append([InlineKeyboardButton(label, callback_data=f"esc:{str(esc['id'])[:8]}")])
    buttons.append([InlineKeyboardButton("Назад", callback_data="exp:menu")])
    return InlineKeyboardMarkup(buttons)


def escalation_detail_keyboard(escalation_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Разрешить", callback_data=f"escr:{escalation_id[:8]}")],
        [InlineKeyboardButton("Назад", callback_data="exp:escalations")],
    ])
