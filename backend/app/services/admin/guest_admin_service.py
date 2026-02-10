"""Guest administration service (split from admin_service)."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    BusinessProfile,
    ContactRequest,
    GuestProfile,
    Project,
    Recommendation,
    Role,
    RoleCode,
    User,
    UserRole,
)
from app.schemas.admin import (
    GuestContactRequestItem,
    GuestDetailResponse,
    GuestListItem,
    GuestProfileInfo,
    GuestRecommendationItem,
)


def _extract_summary(extra_data: dict | None) -> str | None:
    """Get profile summary from extra_data (saved as 'nl_summary', fallback 'summary')."""
    if not extra_data:
        return None
    return extra_data.get("summary") or extra_data.get("nl_summary")


async def list_guests(
    db: AsyncSession,
    event_id: UUID,
    search: str | None = None,
    subtype: str | None = None,
    role_filter: str | None = None,
) -> list[GuestListItem]:
    """List all guests and business partners for an event."""
    guest_role = await db.scalar(select(Role).where(Role.code == RoleCode.GUEST.value))
    business_role = await db.scalar(select(Role).where(Role.code == RoleCode.BUSINESS.value))

    role_ids = []
    if role_filter == "business":
        if business_role:
            role_ids = [business_role.id]
    elif role_filter == "guest":
        if guest_role:
            role_ids = [guest_role.id]
    else:
        if guest_role:
            role_ids.append(guest_role.id)
        if business_role:
            role_ids.append(business_role.id)

    if not role_ids:
        return []

    rec_count_sq = (
        select(func.count(Recommendation.id))
        .select_from(GuestProfile)
        .join(Recommendation, Recommendation.guest_profile_id == GuestProfile.id)
        .where(GuestProfile.user_id == User.id, GuestProfile.event_id == event_id)
        .correlate(User)
        .scalar_subquery()
    )

    contact_count_sq = (
        select(func.count(ContactRequest.id))
        .where(ContactRequest.requester_id == User.id)
        .correlate(User)
        .scalar_subquery()
    )

    has_business_sq = (
        select(func.count(BusinessProfile.id))
        .where(BusinessProfile.user_id == User.id, BusinessProfile.event_id == event_id)
        .correlate(User)
        .scalar_subquery()
    )

    query = (
        select(
            User,
            GuestProfile,
            BusinessProfile,
            Role.code.label("role_code"),
            rec_count_sq.label("rec_count"),
            contact_count_sq.label("contact_count"),
            has_business_sq.label("biz_count"),
        )
        .select_from(UserRole)
        .join(User, UserRole.user_id == User.id)
        .join(Role, UserRole.role_id == Role.id)
        .outerjoin(
            GuestProfile,
            (GuestProfile.user_id == User.id) & (GuestProfile.event_id == event_id),
        )
        .outerjoin(
            BusinessProfile,
            (BusinessProfile.user_id == User.id) & (BusinessProfile.event_id == event_id),
        )
        .where(UserRole.event_id == event_id, UserRole.role_id.in_(role_ids))
    )

    if search:
        pattern = f"%{search}%"
        query = query.where(
            (User.full_name.ilike(pattern)) | (User.username.ilike(pattern))
        )

    if subtype:
        query = query.where(User.guest_subtype == subtype)

    query = query.order_by(User.created_at.desc())
    result = await db.execute(query)
    rows = result.all()

    items = []
    for user, guest_prof, biz_prof, role_code, rec_count, contact_count, biz_count in rows:
        tags: list[str] = []
        keywords: list[str] = []
        profile_summary: str | None = None
        raw_text: str | None = None

        if guest_prof:
            tags = (guest_prof.selected_tags or []) + (guest_prof.extracted_tags or [])
            keywords = guest_prof.keywords or []
            raw_text = guest_prof.raw_text
            extra = guest_prof.extra_data or {}
            profile_summary = _extract_summary(extra)

        if biz_prof and not profile_summary:
            parts = []
            if biz_prof.objective:
                parts.append(biz_prof.objective.value)
            if biz_prof.industries:
                parts.append(", ".join(biz_prof.industries))
            if biz_prof.collaboration_format:
                parts.append(biz_prof.collaboration_format)
            profile_summary = " | ".join(parts) if parts else None
            if not raw_text:
                raw_text = biz_prof.free_text_raw

        items.append(
            GuestListItem(
                id=str(user.id),
                full_name=user.full_name or f"User {user.telegram_user_id}",
                username=user.username,
                telegram_user_id=user.telegram_user_id,
                role=role_code,
                guest_subtype=user.guest_subtype.value if user.guest_subtype else None,
                tags=tags,
                keywords=keywords,
                profile_summary=profile_summary,
                raw_text=raw_text,
                recommendations_count=rec_count or 0,
                contact_requests_count=contact_count or 0,
                has_business_profile=(biz_count or 0) > 0,
                created_at=user.created_at,
            )
        )

    return items


async def get_guest_detail(
    db: AsyncSession,
    event_id: UUID,
    user_id: UUID,
) -> GuestDetailResponse:
    """Get detailed guest profile for admin panel."""
    user = await db.get(User, user_id)
    if not user:
        raise ValueError("User not found")

    # Get user role for this event
    user_role_result = await db.execute(
        select(Role.code)
        .select_from(UserRole)
        .join(Role, UserRole.role_id == Role.id)
        .where(UserRole.user_id == user_id, UserRole.event_id == event_id)
    )
    role_code = user_role_result.scalar_one_or_none()
    if not role_code:
        raise ValueError("User role not found for this event")

    profile = await db.scalar(
        select(GuestProfile).where(
            GuestProfile.user_id == user_id,
            GuestProfile.event_id == event_id,
        )
    )

    bp = await db.scalar(
        select(BusinessProfile).where(
            BusinessProfile.user_id == user_id,
            BusinessProfile.event_id == event_id,
        )
    )

    recommendations: list[GuestRecommendationItem] = []
    if profile:
        rec_result = await db.execute(
            select(Recommendation, Project)
            .join(Project, Recommendation.project_id == Project.id)
            .where(Recommendation.guest_profile_id == profile.id)
            .order_by(Recommendation.rank)
        )
        for rec, project in rec_result.all():
            recommendations.append(
                GuestRecommendationItem(
                    project_title=project.title,
                    relevance_score=rec.relevance_score,
                    rank=rec.rank,
                    category=rec.category,
                )
            )

    contact_result = await db.execute(
        select(ContactRequest, Project, User)
        .join(Project, ContactRequest.project_id == Project.id)
        .join(User, ContactRequest.student_user_id == User.id)
        .where(ContactRequest.requester_id == user_id)
        .order_by(ContactRequest.created_at.desc())
    )
    contact_requests = [
        GuestContactRequestItem(
            project_title=project.title,
            student_name=student.full_name or f"User {student.telegram_user_id}",
            status=cr.status,
            created_at=cr.created_at,
        )
        for cr, project, student in contact_result.all()
    ]

    rec_count = len(recommendations)
    contact_count = len(contact_requests)

    profile_info = None
    if profile:
        extra = profile.extra_data or {}
        profile_info = GuestProfileInfo(
            selected_tags=profile.selected_tags or [],
            keywords=profile.keywords or [],
            raw_text=profile.raw_text,
            interests=extra.get("interests", []),
            goals=extra.get("goals", []),
            summary=_extract_summary(extra),
            company=extra.get("company"),
            position=extra.get("position"),
            partner_status=extra.get("partner_status"),
            business_objectives=extra.get("business_objectives", []),
        )

    biz_dict = None
    if bp:
        biz_dict = {
            "objective": bp.objective.value if bp.objective else None,
            "industries": bp.industries,
            "tech_stack": bp.tech_stack,
            "project_stages": bp.project_stages,
            "collaboration_format": bp.collaboration_format,
        }

    guest_item = GuestListItem(
        id=str(user.id),
        full_name=user.full_name or f"User {user.telegram_user_id}",
        username=user.username,
        telegram_user_id=user.telegram_user_id,
        role=role_code,
        guest_subtype=user.guest_subtype.value if user.guest_subtype else None,
        tags=(profile.selected_tags or []) + (profile.extracted_tags or []) if profile else [],
        keywords=profile.keywords or [] if profile else [],
        profile_summary=_extract_summary(profile.extra_data) if profile else None,
        raw_text=profile.raw_text if profile else None,
        recommendations_count=rec_count,
        contact_requests_count=contact_count,
        has_business_profile=bp is not None,
        created_at=user.created_at,
    )

    return GuestDetailResponse(
        guest=guest_item,
        profile=profile_info,
        business_profile=biz_dict,
        recommendations=recommendations,
        contact_requests=contact_requests,
    )
