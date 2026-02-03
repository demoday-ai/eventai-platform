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
})
