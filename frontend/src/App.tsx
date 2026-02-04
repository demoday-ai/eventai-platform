import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom"
import { Landing } from "./pages/Landing"
import { Login } from "./pages/Login"
import { Dashboard } from "./pages/Dashboard"
import { RoomDetail } from "./pages/RoomDetail"
import { ProjectsList } from "./pages/ProjectsList"
import { DataImport } from "./pages/DataImport"
import { Clustering } from "./pages/Clustering"
import { ExpertMatching } from "./pages/ExpertMatching"
import { ExpertList } from "./pages/ExpertList"
import { Briefing } from "./pages/Briefing"
import { Schedule } from "./pages/Schedule"
import { Coverage } from "./pages/Coverage"
import { CoverageRoomDetail } from "./pages/CoverageRoomDetail"
import { Participation } from "./pages/Participation"
import { Notifications } from "./pages/Notifications"
import { Settings } from "./pages/Settings"
import { ProtectedRoute } from "./components/ProtectedRoute"
import { AppLayout } from "./components/layout/AppLayout"

function App() {
  return (
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
          <Route path="/import" element={<DataImport />} />
          <Route path="/clustering" element={<Clustering />} />
          <Route path="/experts" element={<ExpertMatching />} />
          <Route path="/experts/list" element={<ExpertList />} />
          <Route path="/briefing" element={<Briefing />} />
          <Route path="/coverage" element={<Coverage />} />
          <Route path="/coverage/rooms/:roomId" element={<CoverageRoomDetail />} />
          <Route path="/schedule" element={<Schedule />} />
          <Route path="/participation" element={<Participation />} />
          <Route path="/notifications" element={<Notifications />} />
          <Route path="/projects" element={<ProjectsList />} />
          <Route path="/rooms/:id" element={<RoomDetail />} />
          <Route path="/settings" element={<Settings />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
