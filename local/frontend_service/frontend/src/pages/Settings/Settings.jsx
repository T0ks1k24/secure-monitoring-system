import { useState } from "react";
import { useNavigate } from "react-router-dom";
import CameraSettings from "./CameraSettings";
import "./Settings.scss";

const TABS = [
  { id: "cameras", label: "📷 Камери" },
  { id: "display", label: "🖥️ Відображення" },
  { id: "connection", label: "🔗 Підключення" },
];

export default function Settings() {
  const [activeTab, setActiveTab] = useState("cameras");
  const navigate = useNavigate();

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
      </div>
    </div>
  );
}

function DisplaySettings() {
  const current = parseInt(localStorage.getItem("grid_slot_count") || "9");
  const [slots, setSlots] = useState(current);

  const handleSave = (val) => {
    setSlots(val);
    localStorage.setItem("grid_slot_count", String(val));
  };

  return (
    <div className="tab-content">
      <h2>Відображення</h2>
      <div className="setting-row">
        <label>Кількість слотів на головному екрані</label>
        <div className="slot-options">
          {[4, 6, 9, 12, 16].map(n => (
            <button
              key={n}
              className={`slot-btn ${slots === n ? "active" : ""}`}
              onClick={() => handleSave(n)}
            >
              {n}
            </button>
          ))}
        </div>
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