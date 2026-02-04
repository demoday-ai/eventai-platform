"""Dashboard service for EPIC-011: Organizer Dashboard.

Provides real-time statistics for Demo Day monitoring.
"""

import logging
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.business_profile import BusinessProfile
from app.models.expert_room_assignment import ExpertRoomAssignment
from app.models.participation import ParticipationRequest, ParticipationStatus
from app.models.project import Project
from app.models.role import Role, RoleCode
from app.models.room import Room
from app.models.user import GuestSubtype, User
from app.models.user_role import UserRole
from app.services import matching_service

logger = logging.getLogger(__name__)


@dataclass
class StudentStats:
    """Statistics about student participation."""
    total: int
    confirmed: int
    declined: int
    pending: int
    no_response: int

    @property
    def confirmed_rate(self) -> float:
        return (self.confirmed / self.total * 100) if self.total > 0 else 0

    @property
    def no_show_rate(self) -> float:
        return (self.declined / self.confirmed * 100) if self.confirmed > 0 else 0


@dataclass
class ExpertStats:
    """Statistics about expert coverage."""
    total_invited: int
    confirmed: int
    declined: int
    pending: int
    rooms_total: int
    rooms_covered: int

    @property
    def confirmed_rate(self) -> float:
        return (self.confirmed / self.total_invited * 100) if self.total_invited > 0 else 0

    @property
    def coverage_rate(self) -> float:
        return (self.rooms_covered / self.rooms_total * 100) if self.rooms_total > 0 else 0


@dataclass
class GuestStats:
    """Statistics about guest registration."""
    total: int
    applicants: int
    students: int
    business: int
    other: int


@dataclass
class Alert:
    """Dashboard alert."""
    level: str  # 'critical' or 'warning'
    message: str
    emoji: str


async def get_student_stats(session: AsyncSession, event_id: UUID) -> StudentStats:
    """Get student participation statistics."""
    # Count projects
    total_result = await session.execute(
        select(func.count(Project.id)).where(Project.event_id == event_id)
    )
    total = total_result.scalar() or 0

    # Count by status
    stats_result = await session.execute(
        select(
            ParticipationRequest.status,
            func.count(ParticipationRequest.id)
        )
        .where(ParticipationRequest.event_id == event_id)
        .group_by(ParticipationRequest.status)
    )
    stats_by_status = {row[0]: row[1] for row in stats_result.all()}

    confirmed = stats_by_status.get(ParticipationStatus.CONFIRMED.value, 0)
    declined = stats_by_status.get(ParticipationStatus.DECLINED.value, 0)
    pending = stats_by_status.get(ParticipationStatus.PENDING.value, 0)
    no_response = total - confirmed - declined - pending

    return StudentStats(
        total=total,
        confirmed=confirmed,
        declined=declined,
        pending=pending,
        no_response=no_response,
    )


async def get_expert_stats(session: AsyncSession, event_id: UUID) -> ExpertStats:
    """Get expert coverage statistics."""
    # Get approved clustering
    clustering = await matching_service.get_approved_clustering(session, event_id)
    if not clustering:
        return ExpertStats(0, 0, 0, 0, 0, 0)

    # Count total rooms
    rooms_result = await session.execute(
        select(func.count(Room.id)).where(Room.clustering_run_id == clustering.id)
    )
    rooms_total = rooms_result.scalar() or 0

    # Count assignments by status
    stats_result = await session.execute(
        select(
            ExpertRoomAssignment.status,
            func.count(ExpertRoomAssignment.id)
        )
        .where(ExpertRoomAssignment.clustering_run_id == clustering.id)
        .group_by(ExpertRoomAssignment.status)
    )
    stats_by_status = {row[0]: row[1] for row in stats_result.all()}

    confirmed = stats_by_status.get("confirmed", 0)
    declined = stats_by_status.get("declined", 0)
    pending = stats_by_status.get("pending", 0)
    total_invited = confirmed + declined + pending

    # Count rooms with confirmed experts
    covered_result = await session.execute(
        select(func.count(func.distinct(ExpertRoomAssignment.room_id)))
        .where(ExpertRoomAssignment.clustering_run_id == clustering.id)
        .where(ExpertRoomAssignment.status == "confirmed")
    )
    rooms_covered = covered_result.scalar() or 0

    return ExpertStats(
        total_invited=total_invited,
        confirmed=confirmed,
        declined=declined,
        pending=pending,
        rooms_total=rooms_total,
        rooms_covered=rooms_covered,
    )


async def get_guest_stats(session: AsyncSession, event_id: UUID) -> GuestStats:
    """Get guest registration statistics."""
    # Get guest role
    role_result = await session.execute(
        select(Role).where(Role.code == RoleCode.GUEST.value)
    )
    guest_role = role_result.scalar_one_or_none()
    if not guest_role:
        return GuestStats(0, 0, 0, 0, 0)

    # Count by subtype
    stats_result = await session.execute(
        select(
            User.guest_subtype,
            func.count(User.id)
        )
        .join(UserRole, UserRole.user_id == User.id)
        .where(UserRole.event_id == event_id)
        .where(UserRole.role_id == guest_role.id)
        .group_by(User.guest_subtype)
    )
    stats_by_subtype = {row[0]: row[1] for row in stats_result.all()}

    applicants = stats_by_subtype.get(GuestSubtype.APPLICANT, 0)
    students = stats_by_subtype.get(GuestSubtype.STUDENT, 0)
    other = stats_by_subtype.get(GuestSubtype.OTHER, 0)
    none_subtype = stats_by_subtype.get(None, 0)

    # Count business partners
    business_result = await session.execute(
        select(func.count(func.distinct(BusinessProfile.user_id)))
        .join(UserRole, UserRole.user_id == BusinessProfile.user_id)
        .where(UserRole.event_id == event_id)
    )
    business = business_result.scalar() or 0

    total = applicants + students + other + none_subtype + business

    return GuestStats(
        total=total,
        applicants=applicants,
        students=students,
        business=business,
        other=other + none_subtype,
    )


def get_alerts(
    student_stats: StudentStats,
    expert_stats: ExpertStats,
) -> list[Alert]:
    """Generate alerts based on statistics."""
    alerts = []

    # Critical: Rooms without experts
    uncovered = expert_stats.rooms_total - expert_stats.rooms_covered
    if uncovered > 0:
        alerts.append(Alert(
            level="critical",
            message=f"{uncovered} залов без экспертов!",
            emoji="🚨"
        ))

    # Critical: High decline rate
    if student_stats.total > 0 and student_stats.declined > student_stats.total * 0.2:
        alerts.append(Alert(
            level="critical",
            message=f"Высокий процент отказов: {student_stats.declined} ({student_stats.declined / student_stats.total * 100:.0f}%)",
            emoji="🚨"
        ))

    # Warning: Low confirmation rate
    if student_stats.total > 0 and student_stats.confirmed_rate < 70:
        alerts.append(Alert(
            level="warning",
            message=f"Низкий % подтверждений: {student_stats.confirmed_rate:.0f}%",
            emoji="⚠️"
        ))

    # Warning: Many pending
    if student_stats.pending > 10:
        alerts.append(Alert(
            level="warning",
            message=f"{student_stats.pending} студентов ещё не ответили",
            emoji="⚠️"
        ))

    # Warning: Expert confirmation low
    if expert_stats.total_invited > 0 and expert_stats.confirmed_rate < 50:
        alerts.append(Alert(
            level="warning",
            message=f"Мало подтверждённых экспертов: {expert_stats.confirmed_rate:.0f}%",
            emoji="⚠️"
        ))

    return alerts


async def get_no_show_list(
    session: AsyncSession,
    event_id: UUID,
) -> list[dict]:
    """Get list of students who declined."""
    result = await session.execute(
        select(ParticipationRequest, Project)
        .join(Project, Project.id == ParticipationRequest.project_id)
        .where(ParticipationRequest.event_id == event_id)
        .where(ParticipationRequest.status == ParticipationStatus.DECLINED.value)
    )

    no_shows = []
    for req, project in result.all():
        no_shows.append({
            "project": project.title,
            "author": project.author,
            "contact": project.telegram_contact,
            "reason": req.decline_reason,
        })

    return no_shows


async def get_problem_rooms(
    session: AsyncSession,
    event_id: UUID,
) -> list[dict]:
    """Get rooms without confirmed experts."""
    clustering = await matching_service.get_approved_clustering(session, event_id)
    if not clustering:
        return []

    # Get all rooms
    rooms_result = await session.execute(
        select(Room).where(Room.clustering_run_id == clustering.id)
    )
    rooms = rooms_result.scalars().all()

    # Get rooms with confirmed experts
    covered_result = await session.execute(
        select(ExpertRoomAssignment.room_id)
        .where(ExpertRoomAssignment.clustering_run_id == clustering.id)
        .where(ExpertRoomAssignment.status == "confirmed")
        .distinct()
    )
    covered_ids = {row[0] for row in covered_result.all()}

    # Find uncovered
    problems = []
    for room in rooms:
        if room.id not in covered_ids:
            problems.append({
                "name": room.name,
                "id": str(room.id),
            })

    return problems


def format_dashboard(
    student_stats: StudentStats,
    expert_stats: ExpertStats,
    guest_stats: GuestStats,
    alerts: list[Alert],
    event_name: str,
) -> str:
    """Format dashboard message."""
    lines = [
        f"📊 *Dashboard Demo Day*",
        f"Событие: {event_name}",
        "",
    ]

    # Alerts section
    if alerts:
        lines.append("🚨 *АЛЕРТЫ:*")
        for alert in alerts:
            lines.append(f"{alert.emoji} {alert.message}")
        lines.append("")

    # Students section
    lines.extend([
        "📋 *Студенты:*",
        f"├ Всего проектов: {student_stats.total}",
        f"├ Подтвердили: {student_stats.confirmed} ({student_stats.confirmed_rate:.0f}%)",
        f"├ Отказались: {student_stats.declined}",
        f"├ Ожидают: {student_stats.pending}",
        f"└ Нет ответа: {student_stats.no_response}",
        "",
    ])

    # Experts section
    lines.extend([
        "👨‍🏫 *Эксперты:*",
        f"├ Приглашено: {expert_stats.total_invited}",
        f"├ Подтвердили: {expert_stats.confirmed} ({expert_stats.confirmed_rate:.0f}%)",
        f"└ Покрытие залов: {expert_stats.rooms_covered}/{expert_stats.rooms_total}",
        "",
    ])

    # Guests section
    lines.extend([
        "👥 *Гости:*",
        f"├ Зарегистрировано: {guest_stats.total}",
        f"├ Студенты: {guest_stats.students}",
        f"├ Абитуриенты: {guest_stats.applicants}",
        f"├ Бизнес: {guest_stats.business}",
        f"└ Другое: {guest_stats.other}",
    ])

    return "\n".join(lines)
