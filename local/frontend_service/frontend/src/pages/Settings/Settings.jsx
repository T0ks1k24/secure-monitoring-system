import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useRole } from "../../hooks/useRole";
import CameraSettings from "./CameraSettings/CameraSettings";
import DisplaySettings from "./DisplaySettings/DisplaySettings";
import AccessControl from "./AccessControl";
import "./Settings.scss";

export default function Settings() {
  const [activeTab, setActiveTab] = useState("cameras");
  const navigate = useNavigate();
  const { isAdmin } = useRole();

  const TABS = [
    { id: "cameras", label: "📷 Камери", show: true },
    { id: "display", label: "🖥️ Відображення", show: true},
    { id: "connection", label: "🔗 Підключення", show: isAdmin },
    { id: "access", label: "🔐 Access Control", show: isAdmin },
  ].filter(t => t.show);

  useEffect(() => {
    if (!TABS.find(t => t.id === activeTab)) {
      setActiveTab("cameras");
    }
  }, [isAdmin]);

  return (
    <div className="settings-page">
      <div className="settings-sidebar">
        {TABS.map(tab => (
          <button
            key={tab.id}
            className={`tab-btn ${activeTab === tab.id ? "active" : ""}`}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="settings-content">
        {activeTab === "cameras" && <CameraSettings />}
        {activeTab === "display" && <DisplaySettings />}
        {activeTab === "connection" && <ConnectionSettings />}
        {activeTab === "access" && <AccessControl />}
      </div>
    </div>
  );
}

function ConnectionSettings() {
  const [apiUrl, setApiUrl] = useState(
    localStorage.getItem("api_url") || import.meta.env.VITE_API_URL || "http://localhost:8000"
  );
  const [mediaUrl, setMediaUrl] = useState(
    localStorage.getItem("media_url") || import.meta.env.VITE_MEDIA_MTX_WEBRTC_URL || "http://localhost:8889"
  );
  const [saved, setSaved] = useState(false);

  const handleSave = () => {
    localStorage.setItem("api_url", apiUrl);
    localStorage.setItem("media_url", mediaUrl);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <div className="tab-content">
      <h2>Підключення</h2>
      <div className="setting-row">
        <label>URL бекенду</label>
        <input value={apiUrl} onChange={e => setApiUrl(e.target.value)} placeholder="http://localhost:8000" />
      </div>
      <div className="setting-row">
        <label>URL MediaMTX (WebRTC)</label>
        <input value={mediaUrl} onChange={e => setMediaUrl(e.target.value)} placeholder="http://localhost:8889" />
      </div>
      <button className="save-btn" onClick={handleSave}>
        {saved ? "✓ Збережено" : "Зберегти"}
      </button>
      <p className="hint">Після зміни URL перезапустіть додаток щоб зміни набули чинності.</p>
    </div>
  );
}