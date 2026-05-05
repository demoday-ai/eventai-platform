from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from src.models.project import Project

PAGE_SIZE = 10


def expert_dashboard_keyboard(
    projects: list[Project],
    scored_ids: set,
    page: int = 0,
    page_size: int = PAGE_SIZE,
) -> InlineKeyboardMarkup:
    """Paginated project list. Scored projects show as ✅ with 'Изменить' button.
    Unscored show 'Оценить'. Up to page_size projects per page.
    """
    start = page * page_size
    end = start + page_size
    visible = projects[start:end]
    total_pages = max(1, (len(projects) + page_size - 1) // page_size)

    buttons: list[list[InlineKeyboardButton]] = []
    for p in visible:
        is_scored = p.id in scored_ids
        marker = "✅" if is_scored else "▫️"
        action = "Изменить" if is_scored else "Оценить"
        title = p.title[:30]
        buttons.append([
            InlineKeyboardButton(
                text=f"{marker} #{visible.index(p) + start + 1} {title}",
                callback_data=f"eval:{p.id}",
            ),
            InlineKeyboardButton(
                text=action,
                callback_data=f"eval:{p.id}",
            ),
        ])

    # Pagination row
    nav_row: list[InlineKeyboardButton] = []
    if page > 0:
        nav_row.append(
            InlineKeyboardButton(text="← Пред", callback_data=f"page:{page - 1}")
        )
    nav_row.append(
        InlineKeyboardButton(
            text=f"{page + 1}/{total_pages}", callback_data="page:noop"
        )
    )
    if end < len(projects):
        nav_row.append(
            InlineKeyboardButton(text="След →", callback_data=f"page:{page + 1}")
        )
    if nav_row:
        buttons.append(nav_row)

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def score_keyboard(criterion_index: int, current: int | None = None) -> InlineKeyboardMarkup:
    """1-3 score buttons for a criterion. If current value is given, mark it ✓."""
    row: list[InlineKeyboardButton] = []
    for i in (1, 2, 3):
        label = f"✓ {i}" if current == i else str(i)
        row.append(
            InlineKeyboardButton(text=label, callback_data=f"score:{criterion_index}:{i}")
        )
    return InlineKeyboardMarkup(inline_keyboard=[row])


def confirm_score_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Подтвердить", callback_data="score:confirm"),
            InlineKeyboardButton(text="Назад", callback_data="score:cancel"),
        ],
    ])
