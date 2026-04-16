import "./styles/global.scss";
import TitleBar from "./components/TitleBar/TitleBar";
import { Routes, Route, Navigate } from "react-router-dom";
import { useSelector } from "react-redux";
import Monitoring from "./pages/Monitoring/Monitoring";
import CamerasGrid from "./pages/CamerasGrid/CamerasGrid";
import Settings from "./pages/Settings/Settings";
import Login from "./pages/Login/Login";

if (window.windowAPI?.getWindowId) {
    window.windowAPI.getWindowId().then(id => {
        window.__APP_WINDOW_ID__ = id;
    });
}

function ProtectedRoute({ children }) {
    const token = useSelector(state => state.auth?.accessToken);
    if (!token) return <Navigate to="/login" replace />;
    return children;
}

export default function App() {
    const token = useSelector(state => state.auth?.accessToken);

    return (
        <>
            {token && <TitleBar />}
            <div className={token ? "app-content" : "app-login"}>
                <Routes>
                    <Route path="/login" element={
                        token ? <Navigate to="/" replace /> : <Login />
                    } />
                    <Route path="/" element={<ProtectedRoute><CamerasGrid /></ProtectedRoute>} />
                    <Route path="/monitoring/:cameraId" element={<ProtectedRoute><Monitoring /></ProtectedRoute>} />
                    <Route path="/settings" element={<ProtectedRoute><Settings /></ProtectedRoute>} />
                    <Route path="*" element={<Navigate to={token ? "/" : "/login"} replace />} />
                </Routes>
            </div>
        </>
    );
}