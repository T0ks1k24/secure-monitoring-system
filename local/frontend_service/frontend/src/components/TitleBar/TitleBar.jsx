import { useNavigate, useLocation } from "react-router-dom";
import "./TitleBar.scss"

export default function TitleBar() {
  const navigate = useNavigate();
  const location = useLocation();

  const isMonitoring = location.pathname.startsWith("/monitoring");

  const openNewWindow = () => {
    window.open(window.location.origin, "_blank", "width=1200,height=800");
  };

  return (
    <div id="titlebar">
      <div className="nav-buttons">
        <button onClick={() => navigate(-1)}>🡐</button>
        <button onClick={() => navigate(1)}>🡒</button>
        <button className="popout-main-btn" onClick={openNewWindow} title="Відкрити нове робоче вікно">
          ❐
        </button>
      </div>

      <div className="title">Security System</div>

      <div className="window-buttons">
        {isMonitoring && (
          <button onClick={() => {
            window.windowAPI.toggleKiosk();
            window.dispatchEvent(new CustomEvent("kiosk-toggle"));
          }} title="Режим моніторингу">⛶</button>
        )}
        <button onClick={() => window.windowAPI.minimize()}>—</button>
        <button onClick={() => window.windowAPI.maximize()}>☐</button>
        <button onClick={() => window.windowAPI.close()}>✕</button>
      </div>
    </div>
  )
}