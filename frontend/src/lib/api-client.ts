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
