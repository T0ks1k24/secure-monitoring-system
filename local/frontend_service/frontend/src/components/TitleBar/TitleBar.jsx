import { useNavigate } from "react-router-dom";
import "./TitleBar.scss"

export default function TitleBar() {
  const navigate = useNavigate();

  return (
    <div id="titlebar">
      <div className="nav-buttons">
        <button onClick={() => navigate(-1)}>🡐</button>
        <button onClick={() => navigate(1)}>🡒</button>
      </div>

      <div className="title">Security System</div>

      <div className="window-buttons">
        <button onClick={() => window.windowAPI.minimize()}>—</button>
        <button onClick={() => window.windowAPI.maximize()}>☐</button>
        <button onClick={() => window.windowAPI.close()}>✕</button>
      </div>
    </div>
  )
}