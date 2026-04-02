import { useNavigate } from "react-router-dom";
import { useGetCamerasQuery } from "../../services/camerasApi";
import "./CamerasGrid.scss";

const WEBRTC_BASE = (
  import.meta.env.VITE_MEDIA_MTX_WEBRTC_URL || "http://localhost:8889"
).replace(/\/+$/, "");

const getStreamPath = (rtsp) => {
  if (!rtsp || typeof rtsp !== "string") return "";
  const parts = rtsp.split("/").filter(Boolean);
  return parts.at(-1) || "";
};

export default function CamerasGrid() {
  const navigate = useNavigate();
  const { data: cameras = [], isLoading } = useGetCamerasQuery();

  if (isLoading) return <div className="loading">Завантаження камер...</div>;

  return (
    <div className="cameras-page">
      <div className="page-header">
        <button 
          className="settings-btn" 
          onClick={() => navigate("/settings")} 
          title="Налаштування"
        >
          ⚙️
        </button>
      </div>

      <div className="grid">
        {cameras.length > 0 ? (
          cameras.map((cam) => {
            const streamPath = getStreamPath(cam.rtsp);
            const streamUrl = streamPath ? `${WEBRTC_BASE}/${streamPath}` : "";

            return (
              <div
                key={cam.id}
                className="camera-card"
                onClick={() => navigate(`/monitoring/${cam.id}`)}
              >
                <div className="video-container">
                  {streamUrl ? (
                    <iframe
                      src={streamUrl}
                      style={{
                        width: "100%",
                        height: "100%",
                        border: "none",
                        pointerEvents: "none",
                      }}
                      allow="autoplay; fullscreen"
                    />
                  ) : (
                    <div className="stream-placeholder">
                      Немає stream path в RTSP
                    </div>
                  )}
                </div>
                <div className="camera-label">
                  <span className={`status-dot ${cam.status}`}></span>
                  {cam.name || `Камера ${cam.id}`}
                </div>
              </div>
            );
          })
        ) : (
          <div className="no-cameras">
            Камер не знайдено. Додайте їх у налаштуваннях.
          </div>
        )}
      </div>
    </div>
  );
}
