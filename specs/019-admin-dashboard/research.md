# Research: Dashboard и прогресс

**Feature**: 019-admin-dashboard
**Date**: 2026-02-09

## R-001: Расширение DashboardResponse (projects_count, partners_count)

**Decision**: Добавить поля `projects` (ProjectStats) и `partners` (PartnerStats) в существующий DashboardResponse.

**Rationale**: Текущий DashboardResponse содержит students, experts, guests, rooms. Спецификация требует 5 карточек: проекты, студенты, эксперты, партнёры, залы. Данные для projects_count уже доступны через таблицу `projects` (count where event_id). Для partners_count используем таблицу guests с фильтром по подтипу `partner` + новое поле `source` (bot/import).

**Alternatives considered**:
- Отдельный endpoint GET /api/v1/admin/metrics — отвергнуто: лишний HTTP-вызов, данные уже агрегируются в dashboard_service
- Вычислять на клиенте из guests.by_subtype — отвергнуто: требует знания о подтипах на frontend, нарушает SoC

**Implementation**:
- `backend/app/schemas/admin.py`: добавить `ProjectStats(total: int)`, `PartnerStats(total: int, from_bot: int, from_import: int)`. Добавить поля в `DashboardResponse`
- `backend/app/services/admin/dashboard_service.py`: добавить count(projects) и count(guests where subtype=partner) в `get_dashboard_stats()`
- `frontend/src/lib/api-client.ts`: расширить тип `DashboardData`

---

## R-002: Новый endpoint GET /api/v1/admin/pipeline-status

**Decision**: Создать endpoint, возвращающий статусы 3 фаз и их подшагов. Вся логика определения статусов — на backend.

**Rationale**: Global Stepper и Quick Action требуют знание статуса каждого шага pipeline. Вычисление на клиенте потребовало бы множества API-вызовов и дублирования бизнес-логики. Один endpoint с полной картиной — проще и надёжнее.

**Alternatives considered**:
- Включить в DashboardResponse — отвергнуто: pipeline-status нужен на каждой странице (Global Stepper в layout), а dashboard endpoint вызывается только на Dashboard. Разные lifecycle.
- WebSocket для real-time статуса — отвергнуто: YAGNI. Auto-refresh 30-60 сек достаточен для 3-5 пользователей.

**Implementation**:
- Response schema `PipelineStatusResponse`:
  ```
  phases:
    - name: "data"
      status: "completed" | "in_progress" | "not_started"
      steps:
        - name: "event"
          status: "completed" | "not_started"
          label: "Создать событие"
        - name: "projects"
          status: "completed" | "not_started"
          label: "Загрузить проекты"
        - name: "students"
          ...
        - name: "experts"
          ...
    - name: "distribution"
      steps:
        - name: "clustering"
        - name: "matching"
        - name: "schedule"
    - name: "launch"
      steps:
        - name: "reminders"
        - name: "briefing"
  next_action:
    step: "clustering"
    label: "Запустите кластеризацию по залам"
    link: "/clustering"
  ```
- Логика определения статусов (все данные уже в БД):
  - event: `Event` существует → completed
  - projects: count(Project where event_id) > 0 → completed
  - students: count(ParticipationRequest where event_id) > 0 → completed
  - experts: count(User where role=expert and event_id) > 0 → completed
  - clustering: `ClusteringRun.status == "approved"` → completed
  - matching: count(ExpertRoomAssignment where clustering_run_id=current) > 0 AND approved → completed
  - schedule: `ClusteringRun.schedule_approved_at IS NOT NULL` → completed
  - reminders: count(Notification where type=reminder and event_id) > 0 → completed
  - briefing: count(Notification where type=briefing and event_id) > 0 → completed
- next_action: первый шаг со статусом "not_started" в порядке pipeline

---

## R-003: 5-уровневая шкала покрытия залов

**Decision**: Статус покрытия зала определяется количеством назначенных экспертов: 0=gap, 1=partial, 2=covered, 3=excellent, >3=excess.

**Rationale**: Решение принято стейкхолдером. Текущий API возвращает coverage_status: "full"/"partial"/"none" — нужно расширить до 5 уровней.

**Alternatives considered**:
- Пропорциональный (эксперты/проекты) — отвергнуто стейкхолдером
- Бинарный (есть/нет) — слишком грубый

**Implementation**:
- `backend/app/schemas/admin.py`: изменить `coverage_status` с str на enum: `gap | partial | covered | excellent | excess`
- `backend/app/services/admin/dashboard_service.py`: обновить логику в `get_coverage()`:
  ```python
  def get_coverage_status(expert_count: int) -> str:
      if expert_count == 0: return "gap"
      if expert_count == 1: return "partial"
      if expert_count == 2: return "covered"
      if expert_count == 3: return "excellent"
      return "excess"
  ```
- Frontend маппинг на цвета: gap→red, partial→yellow, covered→green, excellent→green, excess→blue/gray

---

## R-004: Партнёры — единая таблица с флагом источника

**Decision**: Партнёры хранятся в той же таблице `users` с ролью guest и подтипом partner. Добавить поле `source` (enum: bot/import) для отслеживания происхождения.

**Rationale**: В текущей модели guests — это users с role=guest и guest_subtype. Partner — один из подтипов. Единая таблица исключает дублирование. Флаг source позволяет фильтрацию по происхождению.

**Alternatives considered**:
- Отдельная таблица `partners` — отвергнуто: дублирование user-данных, усложнение запросов
- Тег в metadata — отвергнуто: нет стандартного поля, менее надёжно

**Implementation**:
- `backend/app/models/user.py`: добавить поле `source: str | None` (default: "bot"). Enum: "bot", "import"
- Alembic migration: `ALTER TABLE users ADD COLUMN source VARCHAR(10) DEFAULT 'bot'`
- При импорте через admin API: устанавливать source="import"
- При регистрации через бота: source="bot" (default)

---

## R-005: TanStack Query — паттерн auto-refresh без мерцания

**Decision**: Использовать `refetchInterval` в TanStack Query с `keepPreviousData: true` (через `placeholderData`).

**Rationale**: Существующий Dashboard уже использует `refetchInterval: 60000`. TanStack Query v5 при refetch не очищает данные — `data` остаётся предыдущим значением, `isFetching` отслеживает фоновые обновления. Scroll position не зависит от React re-render — DOM обновляется in-place.

**Alternatives considered**:
- SWR (stale-while-revalidate) — отвергнуто: проект уже на TanStack Query
- Polling через setInterval — отвергнуто: TanStack Query делает это лучше (отмена при unmount, dedup, кеширование)

**Implementation**:
```typescript
const { data: dashboard } = useQuery({
  queryKey: ["dashboard"],
  queryFn: getDashboard,
  refetchInterval: 30_000,
  placeholderData: keepPreviousData,
})

const { data: pipeline } = useQuery({
  queryKey: ["pipeline-status"],
  queryFn: getPipelineStatus,
  refetchInterval: 30_000,
  placeholderData: keepPreviousData,
})
```

---

## R-006: GlobalStepper — размещение в layout vs Dashboard

**Decision**: GlobalStepper размещается в AppLayout (header, над content area), вызывается через `usePipelineStatus()` hook. Отображается на всех страницах после авторизации.

**Rationale**: Спецификация (US-002): «На каждой странице приложения организатор видит полосу прогресса». Размещение в layout гарантирует видимость. Данные — через pipeline-status endpoint с auto-refresh.

**Alternatives considered**:
- Только на Dashboard — противоречит спецификации US-002
- Дублирование компонента на каждой странице — нарушает DRY

**Implementation**:
- `frontend/src/components/dashboard/GlobalStepper.tsx`: компонент stepper
- `frontend/src/components/layout/AppLayout.tsx`: добавить GlobalStepper между header и content area
- `frontend/src/hooks/usePipelineStatus.ts`: TanStack Query hook с refetchInterval
