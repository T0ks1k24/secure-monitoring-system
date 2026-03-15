import "./styles/global.scss"
import TitleBar from "./components/TitleBar/TitleBar"
import { Routes, Route } from "react-router-dom"
import Monitoring from "./pages/Monitoring/Monitoring"
import CamerasGrid from "./pages/CamerasGrid/CamerasGrid"
import CameraSettings from "./pages/Settings/CameraSettings"

export default function App() {
  return (
    <>
      <TitleBar />
      <div className="app-content">
        <Routes>

          <Route path="/" element={<CamerasGrid />} />
          <Route path="/monitoring/:cameraId" element={<Monitoring />} />
          <Route path="/settings" element={<CameraSettings/>} />

        </Routes>
      </div>
    </>
  )
}