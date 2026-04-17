import "./styles/global.scss";
import TitleBar from "./components/TitleBar/TitleBar";
import TitleBarMinimal from "./components/TitleBar/TitleBarMinimal";
import { Routes, Route, Navigate } from "react-router-dom";
import { useSelector, useDispatch } from "react-redux";
import { useEffect } from "react";
import { logOut } from "./services/auth/authSlice";
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
    const dispatch = useDispatch();
    useEffect(() => {
        const handleStorage = (e) => {
            if (e.key === "auth-event") {
                try {
                    const event = JSON.parse(e.newValue);
                    if (event?.type === "logout") {
                        dispatch(logOut());
                    }
                } catch {}
            }
        };
        window.addEventListener("storage", handleStorage);
        return () => window.removeEventListener("storage", handleStorage);
    }, [dispatch]);

    const isLoggedIn = !!token;

    return (
        <>
            {isLoggedIn ? <TitleBar /> : <TitleBarMinimal />}
            <div className={isLoggedIn ? "app-content" : "app-login"}>
                <Routes>
                    <Route path="/login" element={
                        isLoggedIn ? <Navigate to="/" replace /> : <Login />
                    } />
                    <Route path="/" element={<ProtectedRoute><CamerasGrid /></ProtectedRoute>} />
                    <Route path="/monitoring/:cameraId" element={<ProtectedRoute><Monitoring /></ProtectedRoute>} />
                    <Route path="/settings" element={<ProtectedRoute><Settings /></ProtectedRoute>} />
                    <Route path="*" element={<Navigate to={isLoggedIn ? "/" : "/login"} replace />} />
                </Routes>
            </div>
        </>
    );
}