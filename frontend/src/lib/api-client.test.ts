import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import MockAdapter from "axios-mock-adapter"
import {
  apiClient,
  getDashboard,
  getCurrentEvent,
  uploadProjects,
  runClustering,
  getCurrentClustering,
  moveProject,
  approveClustering,
  uploadExperts,
  runMatching,
  getCurrentMatching,
  moveExpert,
  approveMatching,
  getInvitePreview,
  confirmInvites,
  generateSchedule,
  getSchedule,
  approveSchedule,
} from "./api-client"

describe("apiClient", () => {
  let mock: MockAdapter

  beforeEach(() => {
    mock = new MockAdapter(apiClient)
    localStorage.clear()
    vi.clearAllMocks()
  })

  afterEach(() => {
    mock.restore()
  })

  describe("interceptors", () => {
    it("handles requests successfully", async () => {
      mock.onGet("/test").reply(200, { success: true })

      const response = await apiClient.get("/test")
      expect(response.status).toBe(200)
      expect(response.data).toEqual({ success: true })
    })

    it("throws on 401 error", async () => {
      mock.onGet("/test").reply(401, { error: "Unauthorized" })

      await expect(apiClient.get("/test")).rejects.toThrow()
    })
  })

  describe("getDashboard", () => {
    it("fetches dashboard data successfully", async () => {
      const mockData = {
        students: { total: 100, confirmed: 80, pending: 15, declined: 5 },
        experts: { total: 50, confirmed: 40, pending: 10, invited: 45 },
        guests: { total: 30, by_subtype: [] },
        rooms: { total: 6, with_experts: 5, without_experts: 1 },
        alerts: [],
      }

      mock.onGet("/admin/dashboard").reply(200, mockData)

      const result = await getDashboard()
      expect(result).toEqual(mockData)
    })

    it("throws error when API fails", async () => {
      mock.onGet("/admin/dashboard").reply(500, { error: "Internal error" })

      await expect(getDashboard()).rejects.toThrow()
    })
  })

  describe("getCurrentEvent", () => {
    it("fetches current event successfully", async () => {
      const mockEvent = {
        id: "event-1",
        name: "Demo Day 2026",
        start_date: "2026-02-06",
        end_date: "2026-02-07",
      }

      mock.onGet("/events/current").reply(200, mockEvent)

      const result = await getCurrentEvent()
      expect(result).toEqual(mockEvent)
    })
  })

  describe("getCoverage", () => {
    it("fetches coverage data successfully", async () => {
      const mockCoverage = [
        {
          room_id: "room-1",
          room_name: "Зал 1: NLP",
          total_experts: 5,
          confirmed_experts: 5,
          projects_count: 20,
          coverage_status: "full",
        },
        {
          room_id: "room-2",
          room_name: "Зал 2: CV",
          total_experts: 4,
          confirmed_experts: 2,
          projects_count: 18,
          coverage_status: "partial",
        },
      ]

      mock.onGet("/admin/coverage").reply(200, mockCoverage)

      const { getCoverage } = await import("./api-client")
      const result = await getCoverage()
      expect(result).toEqual(mockCoverage)
    })

    it("throws error when coverage API fails", async () => {
      mock.onGet("/admin/coverage").reply(500)

      const { getCoverage } = await import("./api-client")
      await expect(getCoverage()).rejects.toThrow()
    })
  })

  describe("getRoomDetail", () => {
    it("fetches room detail successfully", async () => {
      const mockRoomDetail = {
        room: {
          id: "room-1",
          name: "Зал 1: NLP",
          description: "NLP проекты",
        },
        experts: [
          {
            id: "expert-1",
            name: "Иван Иванов",
            status: "confirmed",
            tags: ["NLP"],
          },
        ],
        projects: [
          {
            id: "project-1",
            title: "Чатбот",
            author: "Команда А",
            start_time: "2026-02-06T10:00:00",
            end_time: "2026-02-06T10:15:00",
            status: "confirmed",
          },
        ],
        uncovered_topics: [],
      }

      mock.onGet("/admin/rooms/room-1").reply(200, mockRoomDetail)

      const { getRoomDetail } = await import("./api-client")
      const result = await getRoomDetail("room-1")
      expect(result).toEqual(mockRoomDetail)
    })

    it("throws error when room detail API fails", async () => {
      mock.onGet("/admin/rooms/room-1").reply(404)

      const { getRoomDetail } = await import("./api-client")
      await expect(getRoomDetail("room-1")).rejects.toThrow()
    })
  })

  describe("getProjects", () => {
    it("fetches all projects successfully", async () => {
      const mockProjects = [
        {
          id: "project-1",
          title: "Чатбот для поддержки",
          author: "Команда А",
          room_id: "room-1",
          room_name: "Зал 1: NLP",
          start_time: "2026-02-06T10:00:00",
          end_time: "2026-02-06T10:15:00",
          status: "confirmed",
          tags: ["NLP", "Chatbot"],
        },
        {
          id: "project-2",
          title: "Анализ тональности",
          author: "Команда Б",
          room_id: "room-1",
          room_name: "Зал 1: NLP",
          start_time: "2026-02-06T10:15:00",
          end_time: "2026-02-06T10:30:00",
          status: "pending",
          tags: ["NLP", "Sentiment"],
        },
      ]

      mock.onGet("/admin/projects").reply(200, mockProjects)

      const { getProjects } = await import("./api-client")
      const result = await getProjects()
      expect(result).toEqual(mockProjects)
    })

    it("fetches projects with filters", async () => {
      const mockProjects = [
        {
          id: "project-1",
          title: "Чатбот для поддержки",
          author: "Команда А",
          room_id: "room-1",
          room_name: "Зал 1: NLP",
          start_time: "2026-02-06T10:00:00",
          end_time: "2026-02-06T10:15:00",
          status: "confirmed",
          tags: ["NLP"],
        },
      ]

      mock
        .onGet("/admin/projects", { params: { room_id: "room-1", status: "confirmed" } })
        .reply(200, mockProjects)

      const { getProjects } = await import("./api-client")
      const result = await getProjects({ room_id: "room-1", status: "confirmed" })
      expect(result).toEqual(mockProjects)
    })

    it("throws error when projects API fails", async () => {
      mock.onGet("/admin/projects").reply(500)

      const { getProjects } = await import("./api-client")
      await expect(getProjects()).rejects.toThrow()
    })
  })

  describe("uploadProjects", () => {
    it("uploads projects successfully", async () => {
      const mockResult = { loaded: 10, errors: 0, duplicates: 0, error_details: [], duplicate_titles: [] }
      mock.onPost("/projects/upload").reply(200, mockResult)

      const file = new File(["test"], "projects.csv", { type: "text/csv" })
      const result = await uploadProjects(file, false)
      expect(result).toEqual(mockResult)
    })

    it("throws on upload failure", async () => {
      mock.onPost("/projects/upload").reply(500)

      const file = new File(["test"], "projects.csv", { type: "text/csv" })
      await expect(uploadProjects(file, false)).rejects.toThrow()
    })
  })

  describe("runClustering", () => {
    it("runs clustering successfully", async () => {
      const mockResult = { id: "run-1", status: "completed", num_rooms: 6, feedback: null, rooms: [], created_at: "", approved_at: null }
      mock.onPost("/clustering/run").reply(200, mockResult)

      const result = await runClustering({ num_rooms: 6 })
      expect(result).toEqual(mockResult)
    })
  })

  describe("getCurrentClustering", () => {
    it("fetches current clustering", async () => {
      const mockResult = { id: "run-1", status: "completed", num_rooms: 6, feedback: null, rooms: [], created_at: "", approved_at: null }
      mock.onGet("/clustering/current").reply(200, mockResult)

      const result = await getCurrentClustering()
      expect(result).toEqual(mockResult)
    })

    it("throws 404 when no clustering", async () => {
      mock.onGet("/clustering/current").reply(404)
      await expect(getCurrentClustering()).rejects.toThrow()
    })
  })

  describe("moveProject", () => {
    it("moves project successfully", async () => {
      const mockResult = { id: "run-1", status: "completed", num_rooms: 6, feedback: null, rooms: [], created_at: "", approved_at: null }
      mock.onPost("/clustering/run-1/move").reply(200, mockResult)

      const result = await moveProject("run-1", { project_id: "p1", target_room_id: "r2" })
      expect(result).toEqual(mockResult)
    })
  })

  describe("approveClustering", () => {
    it("approves clustering", async () => {
      mock.onPost("/clustering/run-1/approve").reply(200, { status: "approved" })

      const result = await approveClustering("run-1")
      expect(result).toEqual({ status: "approved" })
    })
  })

  describe("uploadExperts", () => {
    it("uploads experts successfully", async () => {
      const mockResult = { total_parsed: 20, imported: 18, with_tags: 15, without_tags: 3, errors: [] }
      mock.onPost("/experts/upload").reply(200, mockResult)

      const file = new File(["[]"], "experts.json", { type: "application/json" })
      const result = await uploadExperts(file, false)
      expect(result).toEqual(mockResult)
    })
  })

  describe("runMatching", () => {
    it("runs matching successfully", async () => {
      const mockResult = { clustering_run_id: "run-1", total_experts: 10, matched_experts: 8, unmatched_experts: 2, rooms: [] }
      mock.onPost("/matching/run").reply(200, mockResult)

      const result = await runMatching({ use_adjacent_tags: true })
      expect(result).toEqual(mockResult)
    })
  })

  describe("getCurrentMatching", () => {
    it("fetches current matching", async () => {
      const mockResult = { clustering_run_id: "run-1", total_experts: 10, matched_experts: 8, unmatched_experts: 2, rooms: [] }
      mock.onGet("/matching/current").reply(200, mockResult)

      const result = await getCurrentMatching()
      expect(result).toEqual(mockResult)
    })
  })

  describe("moveExpert", () => {
    it("moves expert successfully", async () => {
      const mockResult = { id: "a1", expert_id: "e1", room_id: "r2", room_name: "Зал 2", match_score: 0.5, is_manual: true, status: "proposed" }
      mock.onPost("/matching/a1/move").reply(200, mockResult)

      const result = await moveExpert("a1", "r2")
      expect(result).toEqual(mockResult)
    })
  })

  describe("approveMatching", () => {
    it("approves matching", async () => {
      const mockResult = { approved_count: 8, message: "Approved 8 expert assignments" }
      mock.onPost("/matching/approve").reply(200, mockResult)

      const result = await approveMatching()
      expect(result).toEqual(mockResult)
    })
  })

  describe("getInvitePreview", () => {
    it("fetches invite preview", async () => {
      const mockResult = { total_experts: 10, with_telegram: 8, without_telegram: 2, sample_message: "Hi!", bot_link: "https://t.me/bot" }
      mock.onGet("/invites/preview").reply(200, mockResult)

      const result = await getInvitePreview()
      expect(result).toEqual(mockResult)
    })
  })

  describe("confirmInvites", () => {
    it("confirms invites", async () => {
      const mockResult = { invite_ready_count: 8, bot_link: "https://t.me/bot", message: "Done" }
      mock.onPost("/invites/confirm").reply(200, mockResult)

      const result = await confirmInvites()
      expect(result).toEqual(mockResult)
    })
  })

  describe("generateSchedule", () => {
    it("generates schedule", async () => {
      const mockResult = { total_slots: 20, rooms: [] }
      mock.onPost("/schedule/generate").reply(201, mockResult)

      const result = await generateSchedule({ slot_duration_minutes: 15 })
      expect(result).toEqual(mockResult)
    })
  })

  describe("getSchedule", () => {
    it("fetches schedule", async () => {
      const mockResult = { event_name: "Demo Day", days: [] }
      mock.onGet("/schedule").reply(200, mockResult)

      const result = await getSchedule()
      expect(result).toEqual(mockResult)
    })
  })

  describe("approveSchedule", () => {
    it("approves schedule", async () => {
      const mockResult = { total_slots: 20, rooms: 6, days: 2 }
      mock.onPost("/schedule/approve").reply(200, mockResult)

      const result = await approveSchedule()
      expect(result).toEqual(mockResult)
    })
  })
})
