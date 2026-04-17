import { useNavigate, useLocation } from "react-router-dom";
import { useDispatch } from "react-redux";
import { logOut } from "../../services/auth/authSlice";
import "./TitleBar.scss"


const HomeIcon = () => (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="white" xmlns="http://www.w3.org/2000/svg">
    <path d="M8 1L1 7h2v7h4v-4h2v4h4V7h2L8 1z" />
  </svg>
);

const LogoutIcon = () => (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="white">
    <path d="M6 2H3a1 1 0 0 0-1 1v10a1 1 0 0 0 1 1h3v-1.5H3.5v-9H6V2z" />
    <path d="M10.5 4.5L13.5 8l-3 3.5V9.5H6.5v-3h4V4.5z" />
  </svg>
);

export default function TitleBar() {
  const navigate = useNavigate();
  const location = useLocation();
  const dispatch = useDispatch();

  const isMonitoring = location.pathname.startsWith("/monitoring") || location.pathname === "/";
  const isSettings = location.pathname.startsWith("/settings");

  const openNewWindow = () => {
    window.open(window.location.origin, "_blank", "width=1200,height=800");
  };

  const handleLogout = () => {
    localStorage.setItem("auth-event", JSON.stringify({ type: "logout", ts: Date.now() }));
    dispatch(logOut());
    navigate("/login");
  };

  return (
    <div id="titlebar">
      <div className="nav-buttons">
        <button onClick={() => navigate(-1)}>🡐</button>
        <button onClick={() => navigate(1)}>🡒</button>
        <button onClick={() => navigate("/")} title="Головна"><HomeIcon/></button>
        <button className="popout-main-btn" onClick={openNewWindow} title="Відкрити нове робоче вікно">
          ❐
        </button>
      </div>

      <div className="title">Security System</div>

      <div className="window-buttons">
        {!isSettings && (
          <button onClick={() => navigate("/settings")} title="Налаштування">⚙️</button>
        )}
        {isMonitoring && (
          <button onClick={() => {
            window.windowAPI.toggleKiosk();
            window.dispatchEvent(new CustomEvent("kiosk-toggle"));
          }} title="Режим моніторингу">⛶</button>
        )}
        <button onClick={handleLogout} title="Вийти з системи" className="logout-btn">
          <LogoutIcon />
        </button>
        <button onClick={() => window.windowAPI.minimize()}>—</button>
        <button onClick={() => window.windowAPI.maximize()}>☐</button>
        <button onClick={() => window.windowAPI.close()}>✕</button>
      </div>
    </div>
  )
}