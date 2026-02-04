from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from app.models.role import ROLE_DISPLAY_NAMES, RoleCode
from app.models.user import GUEST_SUBTYPE_DISPLAY, GuestSubtype


def role_keyboard() -> InlineKeyboardMarkup:
    """Two-button role selection: Guest or Partner."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                ROLE_DISPLAY_NAMES[RoleCode.GUEST],
                callback_data=f"role:{RoleCode.GUEST.value}",
            ),
            InlineKeyboardButton(
                ROLE_DISPLAY_NAMES[RoleCode.BUSINESS],
                callback_data=f"role:{RoleCode.BUSINESS.value}",
            ),
        ],
    ])


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


def nl_topic_buttons() -> InlineKeyboardMarkup:
    """Quick-pick topic buttons for NL profiling stage."""
    topics = [
        ("AI / ML", "nl:topic:ai_ml"),
        ("NLP", "nl:topic:nlp"),
        ("Computer Vision", "nl:topic:cv"),
        ("EdTech", "nl:topic:edtech"),
        ("FinTech", "nl:topic:fintech"),
        ("Агенты", "nl:topic:agents"),
        ("MedTech", "nl:topic:medtech"),
        ("Security", "nl:topic:security"),
    ]
    buttons = []
    row = []
    for label, cb in topics:
        row.append(InlineKeyboardButton(label, callback_data=cb))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton("Готово →", callback_data="nl:done")])
    return InlineKeyboardMarkup(buttons)


def confirm_nl_profile_keyboard() -> InlineKeyboardMarkup:
    """Confirm or re-enter NL profile."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✓ Всё верно", callback_data="nlconf:yes")],
        [InlineKeyboardButton("✎ Ввести заново", callback_data="nlconf:retry")],
    ])


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


# --- Business Profiling keyboards ---


def objective_keyboard() -> InlineKeyboardMarkup:
    """Business objective selection: Investment, Hiring, Technology, Partnership."""
    from app.models.business_profile import BusinessObjective, OBJECTIVE_DISPLAY

    buttons = [
        [InlineKeyboardButton(display, callback_data=f"bp:obj:{obj.value}")]
        for obj, display in OBJECTIVE_DISPLAY.items()
    ]
    return InlineKeyboardMarkup(buttons)


def industries_keyboard(selected: list[str] | None = None) -> InlineKeyboardMarkup:
    """Industry selection with multi-select support."""
    selected = selected or []
    industries = [
        ("fintech", "FinTech"),
        ("edtech", "EdTech"),
        ("nlp", "NLP"),
        ("cv", "Computer Vision"),
        ("agents", "AI Agents"),
        ("ml_prod", "ML в продакшене"),
        ("security", "Security"),
        ("medtech", "MedTech"),
        ("other", "Другое"),
    ]
    buttons = []
    for code, display in industries:
        marker = "✓ " if code in selected else ""
        buttons.append([
            InlineKeyboardButton(f"{marker}{display}", callback_data=f"bp:ind:{code}")
        ])
    buttons.append([
        InlineKeyboardButton("Готово →", callback_data="bp:ind:done"),
    ])
    return InlineKeyboardMarkup(buttons)


def stages_keyboard(selected: list[str] | None = None) -> InlineKeyboardMarkup:
    """Project stage selection with multi-select support."""
    selected = selected or []
    stages = [
        ("idea", "Идея"),
        ("mvp", "MVP"),
        ("early_traction", "Ранняя тяга"),
        ("scaling", "Масштабирование"),
        ("mature", "Зрелый продукт"),
    ]
    buttons = []
    for code, display in stages:
        marker = "✓ " if code in selected else ""
        buttons.append([
            InlineKeyboardButton(f"{marker}{display}", callback_data=f"bp:stg:{code}")
        ])
    buttons.append([
        InlineKeyboardButton("Готово →", callback_data="bp:stg:done"),
    ])
    return InlineKeyboardMarkup(buttons)


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


# --- Guest profiling keyboards (EPIC-005) ---


def start_profiling_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Начать профилирование", callback_data="start_profiling")],
    ])


def tag_selection_keyboard(
    tags: list[tuple[str, int]], selected: set[str]
) -> InlineKeyboardMarkup:
    """Inline keyboard with toggle buttons for tag selection (3-column grid).
    tags: list of (tag_name, project_count). selected: set of currently selected tag names.
    """
    buttons = []
    row = []
    # Show top-15 tags by project count
    for tag_name, count in tags[:15]:
        prefix = "✓ " if tag_name in selected else ""
        label = f"{prefix}{tag_name}"
        # Truncate callback data to fit 64-byte limit
        cb_data = f"ptag:{tag_name[:50]}"
        row.append(InlineKeyboardButton(label, callback_data=cb_data))
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    # Action buttons
    buttons.append([
        InlineKeyboardButton("Написать текстом", callback_data="ptag:_text"),
        InlineKeyboardButton("Готово", callback_data="ptag:_done"),
    ])
    return InlineKeyboardMarkup(buttons)


def confirm_profile_keyboard() -> InlineKeyboardMarkup:
    """Confirm or edit extracted profile."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✓ Подтвердить", callback_data="bp:confirm:yes")],
        [InlineKeyboardButton("✎ Исправить", callback_data="bp:confirm:edit")],
        [InlineKeyboardButton("↺ Начать заново", callback_data="bp:confirm:restart")],
    ])


def skip_free_text_keyboard() -> InlineKeyboardMarkup:
    """Skip free text input."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Пропустить →", callback_data="bp:text:skip")],
    ])


def recommendations_page_keyboard(
    page: int,
    total_pages: int,
    items: list,
) -> InlineKeyboardMarkup:
    """Paginated recommendations list."""
    buttons = []

    # Project buttons
    for rec in items:
        score_bar = "●" * (rec.relevance_score // 20) + "○" * (5 - rec.relevance_score // 20)
        bookmark = "⭐" if rec.is_bookmarked else ""
        label = f"{bookmark}{rec.project.title[:30]} [{score_bar}]"
        # Use first 8 chars of UUID for callback (64 byte limit)
        buttons.append([
            InlineKeyboardButton(label, callback_data=f"bp:proj:{str(rec.id)[:8]}")
        ])

    # Navigation row
    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton("◀ Назад", callback_data=f"bp:rec:page:{page - 1}"))
    nav.append(InlineKeyboardButton(f"{page}/{total_pages}", callback_data="bp:noop"))
    if page < total_pages:
        nav.append(InlineKeyboardButton("Вперёд ▶", callback_data=f"bp:rec:page:{page + 1}"))
    if nav:
        buttons.append(nav)

    # Actions row
    buttons.append([
        InlineKeyboardButton("↺ Обновить", callback_data="bp:rec:refresh"),
        InlineKeyboardButton("✎ Профиль", callback_data="bp:rec:edit"),
    ])

    return InlineKeyboardMarkup(buttons)


def project_card_keyboard(recommendation_id: str, is_bookmarked: bool) -> InlineKeyboardMarkup:
    """Single project detail view."""
    bookmark_text = "★ Убрать из избранного" if is_bookmarked else "☆ В избранное"
    rec_id_short = recommendation_id[:8]

    return InlineKeyboardMarkup([
        [InlineKeyboardButton(bookmark_text, callback_data=f"bp:bm:{rec_id_short}")],
        [InlineKeyboardButton("← К списку", callback_data="bp:proj:back")],
    ])


def confirm_interests_keyboard() -> InlineKeyboardMarkup:
    """Confirm extracted interests from free text."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Да", callback_data="prof:yes")],
        [InlineKeyboardButton("Нет, изменить", callback_data="prof:no")],
    ])


def generate_program_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Сгенерировать программу", callback_data="prof:generate")],
        [InlineKeyboardButton("Позже", callback_data="prof:later")],
    ])


def update_profile_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Да, обновить", callback_data="prof:update_yes")],
        [InlineKeyboardButton("Нет", callback_data="prof:update_no")],
    ])


def program_recommendation_keyboard(
    recommendations: list[dict], page: int = 0, page_size: int = 8
) -> InlineKeyboardMarkup:
    """Inline buttons for project details from recommendation list."""
    start_idx = page * page_size
    page_recs = recommendations[start_idx:start_idx + page_size]
    total_pages = max(1, (len(recommendations) + page_size - 1) // page_size)

    buttons = []
    for rec in page_recs:
        label = f"#{rec['rank']} {rec['title'][:35]}"
        pid_short = rec["project_id"][:8]
        buttons.append([InlineKeyboardButton(label, callback_data=f"pdetail:{pid_short}")])

    # Pagination
    if total_pages > 1:
        nav = []
        if page > 0:
            nav.append(InlineKeyboardButton("◀", callback_data=f"recpage:{page - 1}"))
        nav.append(InlineKeyboardButton(f"{page + 1}/{total_pages}", callback_data="noop"))
        if page < total_pages - 1:
            nav.append(InlineKeyboardButton("▶", callback_data=f"recpage:{page + 1}"))
        buttons.append(nav)

    buttons.append([InlineKeyboardButton("Обновить профиль", callback_data="profile:update")])
    return InlineKeyboardMarkup(buttons)


def back_to_program_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Назад к программе", callback_data="prof:back_program")],
    ])


# --- Student schedule acknowledgment keyboards (EPIC-003) ---


def acknowledge_slot_keyboard(request_id: str) -> InlineKeyboardMarkup:
    short_id = str(request_id)[:8]
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Ознакомлен", callback_data=f"ack:{short_id}")],
    ])


def broadcast_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Да, разослать", callback_data="bcast:yes")],
        [InlineKeyboardButton("Отмена", callback_data="bcast:no")],
    ])


def participation_summary_rooms(rooms_data: list) -> InlineKeyboardMarkup:
    buttons = []
    for r in rooms_data:
        ack = r["acknowledged"]
        total = r["total"]
        label = f"{r['room_name'][:20]} ({ack}/{total})"
        buttons.append([InlineKeyboardButton(
            label, callback_data=f"proom:{str(r['room_id'])[:8]}"
        )])
    buttons.append([InlineKeyboardButton("Обновить", callback_data="pstat:refresh")])
    return InlineKeyboardMarkup(buttons)


# --- EPIC-006: Organizer Coverage Dashboard keyboards ---


def coverage_summary_keyboard(rooms_data: list) -> InlineKeyboardMarkup:
    """Coverage summary with room buttons showing status indicators and project counts.

    rooms_data: list of dicts with room_id, room_name, project_count, confirmed, coverage_level.
    """
    indicators = {"covered": "✅", "partial": "⚠️", "uncovered": "❌"}
    buttons = []
    for r in rooms_data:
        ind = indicators.get(r.get("coverage_level", "uncovered"), "❌")
        confirmed = r.get("confirmed", 0)
        projects = r.get("project_count", 0)
        label = f"{ind} {r['room_name'][:18]} — {confirmed} эксп. | {projects} пр."
        buttons.append([InlineKeyboardButton(
            label, callback_data=f"cov_room:{str(r['room_id'])[:8]}"
        )])
    buttons.append([
        InlineKeyboardButton("⚠️ Непокрытые тематики", callback_data="cov:gaps"),
        InlineKeyboardButton("🔄 Обновить", callback_data="cov:refresh"),
    ])
    return InlineKeyboardMarkup(buttons)


def coverage_room_detail_kb(room_id: str) -> InlineKeyboardMarkup:
    """Room detail keyboard with back and refresh buttons."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⬅️ Назад", callback_data="cov:back"),
            InlineKeyboardButton("🔄 Обновить", callback_data=f"cov_rr:{str(room_id)[:8]}"),
        ],
    ])


# --- EPIC-007: DD Reminders keyboards ---


def reminder_type_keyboard() -> InlineKeyboardMarkup:
    """Type selection: day-before or hour-before reminders."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📅 За день", callback_data="rem:type:day")],
        [InlineKeyboardButton("⏰ За час", callback_data="rem:type:hour")],
        [InlineKeyboardButton("Отмена", callback_data="rem:cancel")],
    ])


def reminder_preview_keyboard(batch_id: str) -> InlineKeyboardMarkup:
    """Confirm send or cancel after preview."""
    short_id = str(batch_id)[:8]
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Отправить", callback_data=f"rem:send:{short_id}")],
        [InlineKeyboardButton("❌ Отмена", callback_data="rem:cancel")],
    ])


def reminder_resend_keyboard(batch_id: str) -> InlineKeyboardMarkup:
    """Confirm resend despite duplicate warning."""
    short_id = str(batch_id)[:8]
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Да, отправить повторно", callback_data=f"rem:resend:{short_id}")],
        [InlineKeyboardButton("Отмена", callback_data="rem:cancel")],
    ])


def reminder_recovery_keyboard(batch_id: str) -> InlineKeyboardMarkup:
    """Recovery options for interrupted batch (EPIC-007b).

    Buttons: Resume / Start fresh / Cancel
    """
    short_id = str(batch_id)[:8]
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("▶️ Возобновить", callback_data=f"rem:recover:resume:{short_id}")],
        [InlineKeyboardButton("🔄 Начать заново", callback_data=f"rem:recover:fresh:{short_id}")],
        [InlineKeyboardButton("❌ Отмена", callback_data="rem:cancel")],
    ])
