import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom"
import { Landing } from "./pages/Landing"
import { Login } from "./pages/Login"
import { Dashboard } from "./pages/Dashboard"
import { RoomDetail } from "./pages/RoomDetail"
import { ProjectsList } from "./pages/ProjectsList"
import { ProjectDetail } from "./pages/ProjectDetail"
import { DataImport } from "./pages/DataImport"
import { Clustering } from "./pages/Clustering"
import { Experts } from "./pages/Experts"
import { GuestList } from "./pages/GuestList"
import { Participants } from "./pages/Participants"
import { Schedule } from "./pages/Schedule"
import { CoverageRoomDetail } from "./pages/CoverageRoomDetail"
import { Messaging } from "./pages/Messaging/index"
import { Reminders } from "./pages/Reminders"
import { Event } from "./pages/Event"
import { Tags } from "./pages/Tags"
import { Settings } from "./pages/Settings"
import { AuditLog } from "./pages/AuditLog"
import { ProtectedRoute } from "./components/ProtectedRoute"
import { AppLayout } from "./components/layout/AppLayout"
import { BackgroundJobsProvider } from "./contexts/BackgroundJobsContext"

function App() {
  return (
    <BackgroundJobsProvider>
      <BrowserRouter>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/login" element={<Login />} />
        <Route
          element={
            <ProtectedRoute>
              <AppLayout />
            </ProtectedRoute>
          }
        >
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/event" element={<Event />} />
          <Route path="/import" element={<DataImport />} />
          <Route path="/tags" element={<Tags />} />
          <Route path="/clustering" element={<Clustering />} />
          <Route path="/experts" element={<Experts />} />
          <Route path="/experts/rooms/:roomId" element={<CoverageRoomDetail />} />
          <Route path="/experts/list" element={<Navigate to="/experts" replace />} />
          <Route path="/coverage" element={<Navigate to="/experts" replace />} />
          <Route path="/coverage/rooms/:roomId" element={<CoverageRoomDetail />} />
          <Route path="/schedule" element={<Schedule />} />
          <Route path="/messaging" element={<Messaging />} />
          <Route path="/reminders" element={<Reminders />} />
          <Route path="/participants" element={<Participants />} />
          <Route path="/guests" element={<GuestList />} />
          <Route path="/projects" element={<ProjectsList />} />
          <Route path="/projects/:id" element={<ProjectDetail />} />
          <Route path="/rooms/:id" element={<RoomDetail />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="/audit-log" element={<AuditLog />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
    </BackgroundJobsProvider>
  )
}

export default App
