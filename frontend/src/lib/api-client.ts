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

// API functions
export const getDashboard = async (): Promise<DashboardData> => {
  const { data } = await apiClient.get<DashboardData>("/admin/dashboard")
  return data
}

export const getCurrentEvent = async (): Promise<Event> => {
  const { data } = await apiClient.get<Event>("/events/current")
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
