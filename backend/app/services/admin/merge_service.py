"""Smart merge service: analyze file vs DB, preview changes, apply merge."""

import csv
import io
import json
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.expert import Expert
from app.models.expert_tag import ExpertTag
from app.models.project import Project
from app.models.project_tag import ProjectTag
from app.models.role import RoleCode
from app.models.tag import Tag
from app.models.user import GuestSubtype, User
from app.models.user_role import UserRole
from app.schemas.expert import RowError
from app.schemas.merge import ChangedField, MergeApplyResult, MergePreview, NewItem, UpdatedItem

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Shared file parsing helpers
# ---------------------------------------------------------------------------

def _parse_file(content: bytes, filename: str) -> list[dict]:
    """Parse uploaded file (CSV/JSON/XLSX) into list of row dicts."""
    filename = filename.lower()
    if filename.endswith(".json"):
        data = json.loads(content.decode("utf-8-sig"))
        if not isinstance(data, list):
            raise ValueError("Expected JSON array")
        return data
    elif filename.endswith(".csv"):
        text = content.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))
        return list(reader)
    elif filename.endswith(".xlsx"):
        import openpyxl
        wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
        ws = wb.active
        rows_iter = ws.iter_rows(values_only=True)
        headers = [str(h).strip() if h else f"col_{i}" for i, h in enumerate(next(rows_iter))]
        rows = []
        for row_values in rows_iter:
            if all(v is None for v in row_values):
                continue
            rows.append({
                headers[i]: (str(v).strip() if v is not None else "")
                for i, v in enumerate(row_values)
            })
        wb.close()
        return rows
    else:
        raise ValueError("Unsupported file format")


def _get_field(row: dict, *keys: str) -> str:
    """Get field value with case-insensitive fallback."""
    row_lower = {k.lower().strip(): v for k, v in row.items()}
    for k in keys:
        val = row.get(k) or row_lower.get(k.lower())
        if val:
            return str(val).strip()
    return ""


# ---------------------------------------------------------------------------
# GUEST merge
# ---------------------------------------------------------------------------

async def analyze_guest_merge(
    session: AsyncSession,
    event_id: uuid.UUID,
    content: bytes,
    filename: str,
    subtype: GuestSubtype,
) -> tuple[MergePreview, dict]:
    """Analyze guest file vs DB. Returns (preview, internal_data)."""
    rows = _parse_file(content, filename)

    # Load existing guests for this event + subtype
    guest_role_result = await session.execute(
        select(UserRole)
        .join(UserRole.role)
        .where(
            UserRole.event_id == event_id,
            UserRole.role.has(code=RoleCode.GUEST),
            UserRole.guest_subtype == subtype,
        )
        .options(selectinload(UserRole.user))
    )
    existing_roles = list(guest_role_result.scalars().all())
    db_map: dict[str, tuple[UserRole, User]] = {}
    for ur in existing_roles:
        if ur.user:
            db_map[ur.user.full_name.lower()] = (ur, ur.user)

    new_items: list[NewItem] = []
    updated_items: list[UpdatedItem] = []
    duplicate_count = 0
    errors: list[RowError] = []
    seen_names: set[str] = set()

    # Internal data for apply
    new_rows: list[dict] = []
    update_rows: list[tuple[str, dict]] = []  # (db_key, row)

    for i, row in enumerate(rows):
        name = _get_field(row, "name", "фио *", "фио", "имя *", "имя")
        if not name:
            errors.append(RowError(row=i + 1, field="name", message="Имя обязательно"))
            continue

        name_key = name.lower()
        if name_key in seen_names:
            duplicate_count += 1
            continue
        seen_names.add(name_key)

        telegram = _get_field(row, "telegram", "телеграм *", "телеграм")
        username = telegram.lstrip("@") if telegram else None

        if name_key not in db_map:
            new_items.append(NewItem(name=name, telegram=username))
            new_rows.append({"name": name, "username": username})
        else:
            _, db_user = db_map[name_key]
            changed: list[ChangedField] = []
            if username and (db_user.username or "") != (username or ""):
                changed.append(ChangedField(
                    field="telegram",
                    old_value=db_user.username,
                    new_value=username,
                ))
            if changed:
                updated_items.append(UpdatedItem(
                    name=name,
                    db_id=str(db_user.id),
                    changed_fields=changed,
                ))
                update_rows.append((name_key, {"username": username}))
            else:
                duplicate_count += 1

    preview = MergePreview(
        new_count=len(new_items),
        duplicate_count=duplicate_count,
        updated_count=len(updated_items),
        error_count=len(errors),
        new_items=new_items[:10],
        updated_items=updated_items,
        errors=errors[:20],
    )
    internal = {"new_rows": new_rows, "update_rows": update_rows, "db_map": db_map}
    return preview, internal


async def apply_guest_merge(
    session: AsyncSession,
    event_id: uuid.UUID,
    subtype: GuestSubtype,
    internal: dict,
    add_new: bool = True,
    update_existing: bool = True,
) -> MergeApplyResult:
    """Apply guest merge using internal data from analyze."""
    from app.services.core import user_service

    guest_role = await user_service.get_role_by_code(session, RoleCode.GUEST)
    added = 0
    updated = 0
    skipped = 0
    error_count = 0

    if add_new:
        for row in internal["new_rows"]:
            synthetic_id = f"guest-{uuid.uuid4().hex[:8]}"
            user = await user_service.upsert_user(
                session,
                telegram_user_id=synthetic_id,
                full_name=row["name"],
                username=row["username"],
            )
            await user_service.set_role(
                session,
                user_id=user.id,
                event_id=event_id,
                role=guest_role,
                guest_subtype=subtype,
            )
            added += 1
    else:
        skipped += len(internal["new_rows"])

    if update_existing:
        db_map = internal["db_map"]
        for name_key, updates in internal["update_rows"]:
            if name_key in db_map:
                _, db_user = db_map[name_key]
                if "username" in updates:
                    db_user.username = updates["username"]
                updated += 1
    else:
        skipped += len(internal["update_rows"])

    await session.commit()
    return MergeApplyResult(
        added=added, updated=updated, skipped=skipped, errors=error_count,
    )


# ---------------------------------------------------------------------------
# EXPERT merge
# ---------------------------------------------------------------------------

async def analyze_expert_merge(
    session: AsyncSession,
    event_id: uuid.UUID,
    content: bytes,
    filename: str,
) -> tuple[MergePreview, dict]:
    """Analyze expert file vs DB. Returns (preview, internal_data)."""
    rows = _parse_file(content, filename)

    # Parse rows into standardized format
    parsed = []
    parse_errors: list[RowError] = []
    for i, raw in enumerate(rows):
        name = _get_field(raw, "name", "фио *", "фио", "имя *", "имя")
        if not name:
            parse_errors.append(RowError(row=i + 1, field="name", message="Missing required field"))
            continue
        telegram = _get_field(raw, "telegram", "телеграм *", "телеграм")
        if telegram.startswith("@"):
            telegram = telegram[1:]
        position = _get_field(raw, "position", "описание *", "описание", "должность")
        tags_str = _get_field(raw, "expertise_tags", "tags", "теги *", "теги", "тематики")
        tags_list = [t.strip() for t in tags_str.split(",") if t.strip()] if tags_str else []
        parsed.append({
            "name": name,
            "telegram": telegram,
            "position": position,
            "tags": tags_list,
            "raw": raw,
        })

    # Load existing experts
    result = await session.execute(
        select(Expert)
        .where(Expert.event_id == event_id)
        .options(selectinload(Expert.tags).selectinload(ExpertTag.tag))
    )
    existing = list(result.scalars().all())
    db_map: dict[str, Expert] = {e.name.lower(): e for e in existing}

    new_items: list[NewItem] = []
    updated_items: list[UpdatedItem] = []
    duplicate_count = 0
    seen_names: set[str] = set()

    new_rows: list[dict] = []
    update_rows: list[tuple[str, dict]] = []

    for item in parsed:
        name_key = item["name"].lower()
        if name_key in seen_names:
            duplicate_count += 1
            continue
        seen_names.add(name_key)

        if name_key not in db_map:
            new_items.append(NewItem(name=item["name"], telegram=item["telegram"] or None))
            new_rows.append(item)
        else:
            db_expert = db_map[name_key]
            changed: list[ChangedField] = []

            if item["telegram"] and (db_expert.telegram_username or "") != item["telegram"]:
                changed.append(ChangedField(
                    field="telegram",
                    old_value=db_expert.telegram_username,
                    new_value=item["telegram"],
                ))
            if item["position"] and (db_expert.position or "") != item["position"]:
                changed.append(ChangedField(
                    field="position",
                    old_value=db_expert.position,
                    new_value=item["position"],
                ))

            db_tags = sorted([et.tag.name for et in db_expert.tags]) if db_expert.tags else []
            file_tags = sorted(item["tags"])
            if file_tags and db_tags != file_tags:
                changed.append(ChangedField(
                    field="tags",
                    old_value=", ".join(db_tags),
                    new_value=", ".join(file_tags),
                ))

            if changed:
                updated_items.append(UpdatedItem(
                    name=item["name"],
                    db_id=str(db_expert.id),
                    changed_fields=changed,
                ))
                update_rows.append((name_key, item))
            else:
                duplicate_count += 1

    preview = MergePreview(
        new_count=len(new_items),
        duplicate_count=duplicate_count,
        updated_count=len(updated_items),
        error_count=len(parse_errors),
        new_items=new_items[:10],
        updated_items=updated_items,
        errors=parse_errors[:20],
    )
    internal = {
        "new_rows": new_rows,
        "update_rows": update_rows,
        "db_map": db_map,
    }
    return preview, internal


async def apply_expert_merge(
    session: AsyncSession,
    event_id: uuid.UUID,
    internal: dict,
    add_new: bool = True,
    update_existing: bool = True,
) -> MergeApplyResult:
    """Apply expert merge."""
    from app.services.admin import expert_service

    added = 0
    updated = 0
    skipped = 0

    tag_cache: dict[str, Tag] = {}

    async def _resolve_tag(tag_name: str) -> Tag | None:
        if tag_name in tag_cache:
            return tag_cache[tag_name]
        existing = await session.scalar(select(Tag).where(Tag.name == tag_name))
        if existing:
            tag_cache[tag_name] = existing
            return existing
        tag = Tag(name=tag_name)
        session.add(tag)
        await session.flush()
        tag_cache[tag_name] = tag
        return tag

    if add_new:
        for item in internal["new_rows"]:
            expert = Expert(
                seed_id=f"auto-{uuid.uuid4().hex[:8]}",
                name=item["name"],
                telegram_username=item["telegram"] or None,
                position=item["position"] or None,
                event_id=event_id,
            )
            session.add(expert)
            await session.flush()

            for tag_name in item.get("tags", []):
                tag = await _resolve_tag(tag_name)
                if tag:
                    et = ExpertTag(expert_id=expert.id, tag_id=tag.id)
                    session.add(et)
            added += 1
    else:
        skipped += len(internal["new_rows"])

    if update_existing:
        db_map = internal["db_map"]
        for name_key, item in internal["update_rows"]:
            if name_key in db_map:
                db_expert = db_map[name_key]
                if item["telegram"]:
                    db_expert.telegram_username = item["telegram"]
                if item["position"]:
                    db_expert.position = item["position"]
                if item["tags"]:
                    await expert_service.sync_expert_tags(session, db_expert, item["tags"])
                updated += 1
    else:
        skipped += len(internal["update_rows"])

    await session.commit()
    return MergeApplyResult(added=added, updated=updated, skipped=skipped, errors=0)


# ---------------------------------------------------------------------------
# PROJECT merge
# ---------------------------------------------------------------------------

async def analyze_project_merge(
    session: AsyncSession,
    event_id: uuid.UUID,
    content: bytes,
    filename: str,
) -> tuple[MergePreview, dict]:
    """Analyze project file vs DB. Returns (preview, internal_data)."""
    from app.services.admin.project_service import parse_csv, parse_json, parse_xlsx, validate_rows

    fname = filename.lower()
    if fname.endswith(".csv"):
        raw_rows = parse_csv(content)
    elif fname.endswith(".xlsx"):
        raw_rows = parse_xlsx(content)
    else:
        raw_rows = parse_json(content)

    valid, parse_errors, dup_titles = validate_rows(raw_rows)

    # Load existing projects
    result = await session.execute(
        select(Project)
        .where(Project.event_id == event_id)
        .options(selectinload(Project.tags).selectinload(ProjectTag.tag))
    )
    existing = list(result.scalars().all())
    db_map: dict[str, Project] = {p.title.lower(): p for p in existing}

    # Tag stats
    with_tags = sum(1 for p in existing if p.tags)
    without_tags = sum(1 for p in existing if not p.tags)

    new_items: list[NewItem] = []
    updated_items: list[UpdatedItem] = []
    duplicate_count = 0

    new_rows = []
    update_rows = []

    for row in valid:
        title_key = row.title.lower()
        if title_key not in db_map:
            new_items.append(NewItem(name=row.title, telegram=row.telegram_contact or None))
            new_rows.append(row)
        else:
            db_proj = db_map[title_key]
            changed: list[ChangedField] = []

            if row.description and db_proj.description != row.description:
                old_desc = (db_proj.description or "")[:50]
                new_desc = row.description[:50]
                changed.append(ChangedField(
                    field="description",
                    old_value=old_desc + ("..." if len(db_proj.description or "") > 50 else ""),
                    new_value=new_desc + ("..." if len(row.description) > 50 else ""),
                ))
            if row.author and db_proj.author != row.author:
                changed.append(ChangedField(
                    field="author", old_value=db_proj.author, new_value=row.author,
                ))
            if row.telegram_contact and (db_proj.telegram_contact or "") != row.telegram_contact:
                changed.append(ChangedField(
                    field="telegram_contact",
                    old_value=db_proj.telegram_contact,
                    new_value=row.telegram_contact,
                ))
            if row.track and (db_proj.track or "") != (row.track or ""):
                changed.append(ChangedField(
                    field="track", old_value=db_proj.track, new_value=row.track,
                ))

            if changed:
                updated_items.append(UpdatedItem(
                    name=row.title,
                    db_id=str(db_proj.id),
                    changed_fields=changed,
                ))
                update_rows.append((title_key, row))
            else:
                duplicate_count += 1

    preview = MergePreview(
        new_count=len(new_items),
        duplicate_count=duplicate_count,
        updated_count=len(updated_items),
        error_count=len(parse_errors),
        new_items=new_items[:10],
        updated_items=updated_items,
        errors=parse_errors[:20],
        with_tags_in_db=with_tags,
        missing_tags_in_db=without_tags,
    )
    internal = {
        "new_rows": new_rows,
        "update_rows": update_rows,
        "db_map": db_map,
        "parse_errors": parse_errors,
    }
    return preview, internal


async def apply_project_merge(
    session: AsyncSession,
    event_id: uuid.UUID,
    internal: dict,
    add_new: bool = True,
    update_existing: bool = True,
) -> MergeApplyResult:
    """Apply project merge."""
    from app.services.admin.project_service import _get_candidate_tags, _parse_tags

    added = 0
    updated = 0
    skipped = 0

    tag_cache: dict[str, Tag] = {}
    candidate_tags = await _get_candidate_tags(session)
    candidate_set = set(candidate_tags)

    async def _resolve_tag(tag_name: str) -> Tag | None:
        if tag_name not in candidate_set:
            return None
        if tag_name in tag_cache:
            return tag_cache[tag_name]
        existing = await session.scalar(select(Tag).where(Tag.name == tag_name))
        if existing:
            tag_cache[tag_name] = existing
            return existing
        return None

    if add_new:
        for row in internal["new_rows"]:
            project = Project(
                event_id=event_id,
                title=row.title,
                description=row.description,
                author=row.author,
                telegram_contact=row.telegram_contact,
                track=row.track,
                source="upload",
            )
            session.add(project)
            await session.flush()

            tag_names = _parse_tags(row.tags) if row.tags else []
            for tn in tag_names:
                tag = await _resolve_tag(tn)
                if tag:
                    pt = ProjectTag(project_id=project.id, tag_id=tag.id)
                    session.add(pt)
            added += 1
    else:
        skipped += len(internal["new_rows"])

    if update_existing:
        db_map = internal["db_map"]
        for title_key, row in internal["update_rows"]:
            if title_key in db_map:
                db_proj = db_map[title_key]
                if row.description:
                    db_proj.description = row.description
                if row.author:
                    db_proj.author = row.author
                if row.telegram_contact:
                    db_proj.telegram_contact = row.telegram_contact
                if row.track:
                    db_proj.track = row.track
                updated += 1
    else:
        skipped += len(internal["update_rows"])

    await session.commit()
    return MergeApplyResult(added=added, updated=updated, skipped=skipped, errors=0)
