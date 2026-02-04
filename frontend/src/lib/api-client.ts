import axios from "axios"

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1"

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
})

// Add auth token to requests
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem("auth_token")
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Handle auth errors
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("auth_token")
      window.location.href = "/login"
    }
    return Promise.reject(error)
  }
)

// Types
export interface StudentStats {
  total: number
  confirmed: number
  pending: number
  declined: number
}

export interface ExpertStats {
  total: number
  confirmed: number
  pending: number
  invited: number
}

export interface GuestSubtypeCount {
  subtype: string
  count: number
}

export interface GuestStats {
  total: number
  by_subtype: GuestSubtypeCount[]
}

export interface RoomStats {
  total: number
  with_experts: number
  without_experts: number
}

export interface Alert {
  severity: "critical" | "warning" | "info"
  message: string
  room_id?: string
  room_name?: string
}

export interface DashboardData {
  students: StudentStats
  experts: ExpertStats
  guests: GuestStats
  rooms: RoomStats
  alerts: Alert[]
}

export interface Event {
  id: string
  name: string
  start_date: string
  end_date: string | null
  description?: string | null
}

export interface EventUpdateRequest {
  name?: string
  start_date?: string
  end_date?: string
  description?: string
}

export interface RoomCoverage {
  room_id: string
  room_name: string
  total_experts: number
  confirmed_experts: number
  projects_count: number
  coverage_status: "full" | "partial" | "none"
}

export interface RoomInfo {
  id: string
  name: string
  description: string
}

export interface ExpertInfo {
  id: string
  name: string
  status: "confirmed" | "pending" | "declined"
  tags: string[]
}

export interface ProjectInfo {
  id: string
  title: string
  author: string
  start_time: string
  end_time: string
  status: "confirmed" | "pending" | "cancelled"
}

export interface RoomDetailData {
  room: RoomInfo
  experts: ExpertInfo[]
  projects: ProjectInfo[]
  uncovered_topics: string[]
}

export interface ProjectListItem {
  id: string
  title: string
  author: string
  room_id: string
  room_name: string
  start_time: string
  end_time: string
  status: "confirmed" | "pending" | "cancelled"
  tags: string[]
}

export interface ProjectsListParams {
  room_id?: string
  status?: string
  search?: string
}

// --- Expert list types ---

export interface ExpertListItem {
  id: string
  seed_id: string
  name: string
  telegram_username: string | null
  position: string | null
  tags: string[]
  bot_started: boolean
  assignment_status: string | null
}

export interface ExpertCreateRequest {
  name: string
  telegram_username?: string | null
  position?: string | null
  tags?: string[]
}

export interface ExpertUpdateRequest {
  name?: string | null
  telegram_username?: string | null
  position?: string | null
  tags?: string[] | null
}

// --- Upload / Import types ---

export interface RowError {
  row: number
  field: string
  message: string
}

export interface UploadResult {
  loaded: number
  errors: number
  duplicates: number
  error_details: RowError[]
  duplicate_titles: string[]
}

export interface UploadConflict {
  message: string
  existing_count: number
  new_count: number
}

export interface ExpertUploadResult {
  total_parsed: number
  imported: number
  with_tags: number
  without_tags: number
  errors: RowError[]
}

export interface ExpertUploadConflict {
  existing_count: number
  message: string
}

// --- Guest Upload types ---

export interface GuestUploadResult {
  total_parsed: number
  imported: number
  duplicates: number
  errors: RowError[]
}

export interface GuestUploadConflict {
  existing_count: number
  message: string
}

// --- Clustering types ---

export interface ClusteringRequest {
  num_rooms: number
  feedback?: string | null
}

export interface ClusteringProject {
  id: string
  title: string
  description: string
  tags: string[]
  author: string
  telegram_contact: string
  source: string
  room: { id: string; name: string } | null
}

export interface ClusteringRoom {
  id: string
  name: string
  theme_rationale: string
  project_count: number
  projects: ClusteringProject[]
}

export interface ClusteringResult {
  id: string
  status: string
  num_rooms: number
  feedback: string | null
  rooms: ClusteringRoom[]
  created_at: string
  approved_at: string | null
}

export interface MoveProjectRequest {
  project_id: string
  target_room_id: string
}

// --- Matching types ---

export interface MatchingRequest {
  use_adjacent_tags?: boolean
}

export interface RoomMatchExpert {
  expert_id: string
  name: string
  match_score: number
  matching_tags: string[]
  is_manual: boolean
}

export interface RoomMatchSummary {
  room_id: string
  room_name: string
  expert_count: number
  experts: RoomMatchExpert[]
}

export interface MatchingResult {
  clustering_run_id: string
  total_experts: number
  matched_experts: number
  unmatched_experts: number
  rooms: RoomMatchSummary[]
}

export interface MoveExpertResult {
  id: string
  expert_id: string
  room_id: string
  room_name: string
  match_score: number
  is_manual: boolean
  status: string
}

export interface ApproveResult {
  approved_count: number
  message: string
}

// --- Invite types ---

export interface InvitePreview {
  total_experts: number
  with_telegram: number
  without_telegram: number
  sample_message: string
  bot_link: string
}

export interface InviteConfirmResult {
  invite_ready_count: number
  bot_link: string
  message: string
}

// --- Schedule types ---

export interface ScheduleGenerateRequest {
  clustering_run_id?: string | null
  day1_start?: string | null
  day1_end?: string | null
  day2_start?: string | null
  day2_end?: string | null
  slot_duration_minutes?: number
}

export interface ScheduleRoomSummary {
  room_id: string
  room_name: string
  slot_count: number
  first_slot: string | null
  last_slot: string | null
}

export interface ScheduleGenerateResult {
  total_slots: number
  rooms: ScheduleRoomSummary[]
}

export interface ScheduleSlotResponse {
  id: string
  room_id: string
  room_name: string
  project_id: string
  project_title: string
  project_author: string | null
  start_time: string
  end_time: string
  display_order: number
  status: string
}

export interface RoomSchedule {
  room_id: string
  room_name: string
  slots: ScheduleSlotResponse[]
}

export interface DaySchedule {
  date: string
  rooms: RoomSchedule[]
}

export interface ScheduleResponse {
  event_name: string
  days: DaySchedule[]
}

export interface ScheduleApproveResult {
  total_slots: number
  rooms: number
  days: number
}

// --- Coverage types ---

export interface CoverageRoom {
  room_id: string
  room_name: string
  project_count: number
  top_tags: string[]
  confirmed: number
  pending: number
  declined: number
  total_assigned: number
  coverage_level: "full" | "partial" | "none"
}

export interface CoverageTotals {
  confirmed: number
  pending: number
  declined: number
  total_needed: number
  coverage_percent: number
}

export interface CoverageSummaryData {
  rooms: CoverageRoom[]
  totals: CoverageTotals
}

export interface ExpertCandidate {
  expert_id: string
  name: string
  matching_tags: string[]
  current_rooms: string[]
}

export interface CoverageGap {
  room_id: string
  room_name: string
  uncovered_tag: string
  project_count_with_tag: number
  candidates: ExpertCandidate[]
}

export interface CoverageGapsList {
  total_gaps: number
  gaps: CoverageGap[]
}

export interface CoverageRoomExpert {
  expert_id: string
  name: string
  status: string
  match_score: number
  tags: string[]
  bot_started: boolean
}

export interface RoomCoverageDetail {
  room_id: string
  room_name: string
  project_count: number
  project_tags: string[]
  experts: CoverageRoomExpert[]
  uncovered_tags: string[]
  candidates: ExpertCandidate[]
}

// --- Escalation types ---

export interface EscalationItem {
  id: string
  type: string
  expert_name: string
  room_name: string
  message: string
  resolved: boolean
  created_at: string
}

// --- Participation types ---

export interface BroadcastResult {
  sent: number
  skipped: number
  failed: number
  unregistered: number
  unregistered_projects: string[]
}

export interface ParticipationRoomSummary {
  room_id: string
  room_name: string
  total: number
  acknowledged: number
  pending: number
}

export interface ParticipationSummary {
  total: number
  acknowledged: number
  pending: number
  unregistered: number
  by_room: ParticipationRoomSummary[]
}

export interface UnacknowledgedItem {
  request_id: string
  project_title: string
  author_name: string
  telegram_contact: string
  room_name: string
  status: string
  sent_at: string
  reminder_sent: boolean
  escalated: boolean
}

export interface UnacknowledgedList {
  items: UnacknowledgedItem[]
  total: number
}

// --- Reminder types (schedule.py — JWT auth) ---

export interface RecipientCounts {
  students: number
  experts: number
  guests: number
  business: number
  total: number
}

export interface SampleMessages {
  student: string | null
  expert: string | null
  guest: string | null
  business: string | null
}

export interface UnreachableParticipant {
  user_id: string
  name: string
  role: string
  reason: string
}

export interface ScheduleReminderPreview {
  day: string
  scheduled_send_time: string
  can_cancel: boolean
  recipients: RecipientCounts
  sample_messages: SampleMessages
  unreachable: UnreachableParticipant[]
}

export interface ReminderSendResult {
  day: string
  sent: number
  failed: number
  skipped: number
}

export interface ReminderCancelResult {
  cancelled_count: number
  day: string
}

// --- Reminder types (reminders.py — query param auth) ---

export interface ReminderBatchSummary {
  id: string
  reminder_type: string
  status: string
  initiated_by_name: string
  total_recipients: number
  sent: number
  failed: number
  skipped: number
  started_at: string
  completed_at: string | null
}

export interface ReminderBatchDetail extends ReminderBatchSummary {
  by_recipient_type: Record<string, { sent: number; failed: number; skipped: number }>
}

export interface ReminderBatchListResponse {
  batches: ReminderBatchSummary[]
}

export interface RolePreview {
  count: number
  skipped: number
  declined: number
}

export interface BatchReminderPreview {
  reminder_type: string
  by_role: Record<string, RolePreview>
  total_recipients: number
  total_skipped: number
  duplicate_warning: boolean
}

// --- Notification types ---

export interface StatusSummaryData {
  total: number
  sent: number
  failed: number
  pending: number
}

export interface RoleStatsItem {
  role: string
  sent: number
  failed: number
  pending: number
}

export interface TypeStatsItem {
  type: string
  sent: number
  failed: number
  pending: number
}

export interface NotificationDashboardData {
  summary: StatusSummaryData
  by_role: RoleStatsItem[]
  by_type: TypeStatsItem[]
  unreachable: UnreachableParticipant[]
}

export interface NotificationItem {
  id: string
  user_name: string
  type: string
  status: string
  scheduled_at: string
  sent_at: string | null
  error_message: string | null
  retry_count: number
}

export interface NotificationListResponse {
  total: number
  items: NotificationItem[]
}

// --- Schedule edit types ---

export interface SlotUpdateRequest {
  start_time?: string
  end_time?: string
  room_id?: string
  status?: string
}

export interface SlotUpdateResult {
  slot: ScheduleSlotResponse
  change_log_id: string
  notifications_queued: number
}

export interface ScheduleChangeItem {
  id: string
  slot_id: string
  project_title: string
  change_type: string
  old_start_time: string | null
  new_start_time: string | null
  old_room_name: string | null
  new_room_name: string | null
  changed_by: string
  created_at: string
  notifications_sent: number
}

export interface ScheduleChangeListResponse {
  total: number
  items: ScheduleChangeItem[]
}

// API functions
export const getDashboard = async (): Promise<DashboardData> => {
  const { data } = await apiClient.get<DashboardData>("/admin/dashboard")
  return data
}

export const getCurrentEvent = async (): Promise<Event> => {
  const { data } = await apiClient.get<Event>("/events/current")
  return data
}

export const updateCurrentEvent = async (body: EventUpdateRequest): Promise<Event> => {
  const { data } = await apiClient.patch<Event>("/admin/events/current", body)
  return data
}

export const getCoverage = async (): Promise<RoomCoverage[]> => {
  const { data } = await apiClient.get<RoomCoverage[]>("/admin/coverage")
  return data
}

export const getRoomDetail = async (roomId: string): Promise<RoomDetailData> => {
  const { data } = await apiClient.get<RoomDetailData>(`/admin/rooms/${roomId}`)
  return data
}

export const getProjects = async (params?: ProjectsListParams): Promise<ProjectListItem[]> => {
  const { data } = await apiClient.get<ProjectListItem[]>("/admin/projects", { params })
  return data
}

// --- Project Upload ---

export const uploadProjects = async (file: File, replace: boolean): Promise<UploadResult> => {
  const formData = new FormData()
  formData.append("file", file)
  const { data } = await apiClient.post<UploadResult>("/projects/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
    params: { replace },
  })
  return data
}

// --- Clustering ---

export const runClustering = async (params: ClusteringRequest): Promise<ClusteringResult> => {
  const { data } = await apiClient.post<ClusteringResult>("/clustering/run", params)
  return data
}

export const getCurrentClustering = async (): Promise<ClusteringResult> => {
  const { data } = await apiClient.get<ClusteringResult>("/clustering/current")
  return data
}

export const moveProject = async (
  runId: string,
  body: MoveProjectRequest
): Promise<ClusteringResult> => {
  const { data } = await apiClient.post<ClusteringResult>(`/clustering/${runId}/move`, body)
  return data
}

export const approveClustering = async (runId: string): Promise<{ status: string }> => {
  const { data } = await apiClient.post<{ status: string }>(`/clustering/${runId}/approve`)
  return data
}

// --- Expert Upload ---

export const uploadExperts = async (
  file: File,
  confirmReplace: boolean
): Promise<ExpertUploadResult> => {
  const formData = new FormData()
  formData.append("file", file)
  const { data } = await apiClient.post<ExpertUploadResult>("/experts/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
    params: { confirm_replace: confirmReplace },
  })
  return data
}

// --- Guest Upload ---

export const uploadGuests = async (
  file: File,
  defaultSubtype: string,
  confirmReplace: boolean
): Promise<GuestUploadResult> => {
  const formData = new FormData()
  formData.append("file", file)
  const { data } = await apiClient.post<GuestUploadResult>("/admin/guests/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
    params: { default_subtype: defaultSubtype, confirm_replace: confirmReplace },
  })
  return data
}

// --- Expert CRUD ---

export const getExperts = async (params?: { search?: string }): Promise<ExpertListItem[]> => {
  const { data } = await apiClient.get<ExpertListItem[]>("/experts", { params })
  return data
}

export const createExpert = async (body: ExpertCreateRequest): Promise<ExpertListItem> => {
  const { data } = await apiClient.post<ExpertListItem>("/experts", body)
  return data
}

export const updateExpert = async (id: string, body: ExpertUpdateRequest): Promise<ExpertListItem> => {
  const { data } = await apiClient.patch<ExpertListItem>(`/experts/${id}`, body)
  return data
}

// --- Matching ---

export const runMatching = async (params?: MatchingRequest): Promise<MatchingResult> => {
  const { data } = await apiClient.post<MatchingResult>("/matching/run", params || {})
  return data
}

export const getCurrentMatching = async (): Promise<MatchingResult> => {
  const { data } = await apiClient.get<MatchingResult>("/matching/current")
  return data
}

export const moveExpert = async (
  assignmentId: string,
  targetRoomId: string
): Promise<MoveExpertResult> => {
  const { data } = await apiClient.post<MoveExpertResult>(`/matching/${assignmentId}/move`, {
    target_room_id: targetRoomId,
  })
  return data
}

export const approveMatching = async (): Promise<ApproveResult> => {
  const { data } = await apiClient.post<ApproveResult>("/matching/approve")
  return data
}

// --- Invites ---

export const getInvitePreview = async (): Promise<InvitePreview> => {
  const { data } = await apiClient.get<InvitePreview>("/invites/preview")
  return data
}

export const confirmInvites = async (): Promise<InviteConfirmResult> => {
  const { data } = await apiClient.post<InviteConfirmResult>("/invites/confirm")
  return data
}

// --- Schedule ---

export const generateSchedule = async (
  params?: ScheduleGenerateRequest
): Promise<ScheduleGenerateResult> => {
  const { data } = await apiClient.post<ScheduleGenerateResult>("/schedule/generate", params || {})
  return data
}

export const getSchedule = async (params?: {
  room_id?: string
  day?: string
  status?: string
}): Promise<ScheduleResponse> => {
  const { data } = await apiClient.get<ScheduleResponse>("/schedule", { params })
  return data
}

export const approveSchedule = async (): Promise<ScheduleApproveResult> => {
  const { data } = await apiClient.post<ScheduleApproveResult>("/schedule/approve")
  return data
}

// --- Coverage ---

export const getCoverageSummary = async (): Promise<CoverageSummaryData> => {
  const { data } = await apiClient.get<CoverageSummaryData>("/coverage")
  return data
}

export const getCoverageGaps = async (): Promise<CoverageGapsList> => {
  const { data } = await apiClient.get<CoverageGapsList>("/coverage/gaps")
  return data
}

export const getRoomCoverageDetail = async (roomId: string): Promise<RoomCoverageDetail> => {
  const { data } = await apiClient.get<RoomCoverageDetail>(`/coverage/${roomId}`)
  return data
}

// --- Escalations ---

export const getEscalations = async (resolved?: boolean): Promise<EscalationItem[]> => {
  const { data } = await apiClient.get<EscalationItem[]>("/escalations", {
    params: resolved !== undefined ? { resolved } : undefined,
  })
  return data
}

export const resolveEscalation = async (id: string): Promise<EscalationItem> => {
  const { data } = await apiClient.post<EscalationItem>(`/escalations/${id}/resolve`)
  return data
}

// --- Participation ---

export const broadcastParticipation = async (): Promise<BroadcastResult> => {
  const { data } = await apiClient.post<BroadcastResult>("/participation/broadcast")
  return data
}

export const getParticipationSummary = async (roomId?: string): Promise<ParticipationSummary> => {
  const { data } = await apiClient.get<ParticipationSummary>("/participation/summary", {
    params: roomId ? { room_id: roomId } : undefined,
  })
  return data
}

export const getUnacknowledged = async (roomId?: string): Promise<UnacknowledgedList> => {
  const { data } = await apiClient.get<UnacknowledgedList>("/participation/unacknowledged", {
    params: roomId ? { room_id: roomId } : undefined,
  })
  return data
}

// --- Reminders (schedule.py — JWT auth) ---

export const getScheduleReminderPreview = async (day?: string): Promise<ScheduleReminderPreview> => {
  const { data } = await apiClient.get<ScheduleReminderPreview>("/reminders/preview", {
    params: day ? { day } : undefined,
  })
  return data
}

export const sendReminders = async (day: string): Promise<ReminderSendResult> => {
  const { data } = await apiClient.post<ReminderSendResult>("/reminders/send", { day })
  return data
}

export const cancelReminders = async (day: string): Promise<ReminderCancelResult> => {
  const { data } = await apiClient.post<ReminderCancelResult>("/reminders/cancel", { day })
  return data
}

// --- Reminders (reminders.py — query param auth) ---

export const getReminderBatches = async (
  telegramId: string,
  params?: { status?: string; type?: string }
): Promise<ReminderBatchListResponse> => {
  const { data } = await apiClient.get<ReminderBatchListResponse>("/reminders/batches", {
    params: { telegram_user_id: telegramId, ...params },
  })
  return data
}

export const getReminderBatchDetail = async (
  batchId: string,
  telegramId: string
): Promise<ReminderBatchDetail> => {
  const { data } = await apiClient.get<ReminderBatchDetail>(`/reminders/batches/${batchId}`, {
    params: { telegram_user_id: telegramId },
  })
  return data
}

export const previewReminderBatch = async (
  telegramId: string,
  type: string
): Promise<BatchReminderPreview> => {
  const { data } = await apiClient.post<BatchReminderPreview>("/reminders/preview", {
    reminder_type: type,
    telegram_user_id: telegramId,
  })
  return data
}

// --- Notifications ---

export const getNotificationDashboard = async (params?: {
  type?: string
  day?: string
}): Promise<NotificationDashboardData> => {
  const { data } = await apiClient.get<NotificationDashboardData>("/notifications/dashboard", { params })
  return data
}

export const getNotifications = async (params?: {
  type?: string
  status?: string
  offset?: number
  limit?: number
}): Promise<NotificationListResponse> => {
  const { data } = await apiClient.get<NotificationListResponse>("/notifications", { params })
  return data
}

// --- Schedule edits ---

export const updateSlot = async (
  slotId: string,
  body: SlotUpdateRequest
): Promise<SlotUpdateResult> => {
  const { data } = await apiClient.patch<SlotUpdateResult>(`/schedule/slots/${slotId}`, body)
  return data
}

export const getScheduleChanges = async (params?: {
  offset?: number
  limit?: number
}): Promise<ScheduleChangeListResponse> => {
  const { data } = await apiClient.get<ScheduleChangeListResponse>("/schedule/changes", { params })
  return data
}

// --- Briefing types ---

export interface BriefingPreview {
  expert_count: number
  with_telegram: number
  without_telegram: number
}

export interface BriefingSendResult {
  sent: number
  failed: number
  skipped: number
}

// --- Briefing ---

export const getBriefingPreview = async (): Promise<BriefingPreview> => {
  const { data } = await apiClient.get<BriefingPreview>("/admin/briefing/preview")
  return data
}

export const sendBriefing = async (): Promise<BriefingSendResult> => {
  const { data } = await apiClient.post<BriefingSendResult>("/admin/briefing/send")
  return data
}
