import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import MockAdapter from "axios-mock-adapter"
import { apiClient, getDashboard, getCurrentEvent } from "./api-client"

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
})
