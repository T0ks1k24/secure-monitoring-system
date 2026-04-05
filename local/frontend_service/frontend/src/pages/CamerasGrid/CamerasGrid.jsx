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

const DEFAULT_SLOT_COUNT = 9;

const getGridLayout = (count) => {
  if (count === 4)  return { cols: 2, rows: 2 };
  if (count === 6)  return { cols: 3, rows: 2 };
  if (count === 9)  return { cols: 3, rows: 3 };
  if (count === 12) return { cols: 4, rows: 3 };
  if (count === 16) return { cols: 4, rows: 4 };
  return { cols: 3, rows: 3 };
};

export default function CamerasGrid() {
  const navigate = useNavigate();
  const { data: cameras = [], isLoading } = useGetCamerasQuery();

  const slotCount = parseInt(localStorage.getItem("grid_slot_count") || DEFAULT_SLOT_COUNT);
  const { cols, rows } = getGridLayout(slotCount);
  const slotConfig = (() => {
    try {
      const saved = localStorage.getItem("slot_config");
      if (!saved) return Array(slotCount).fill(null);
      const parsed = JSON.parse(saved);
      const result = Array(slotCount).fill(null);
      parsed.forEach((id, i) => { if (i < slotCount) result[i] = id; });
      return result;
    } catch { return Array(slotCount).fill(null); }
  })();

  const slots = slotConfig.map(id =>
    id ? cameras.find(c => String(c.id) === String(id)) || null : null
  );

  if (isLoading) return <div className="loading">Завантаження камер...</div>;

  return (
    <div className="cameras-page">
      <div
        className="grid"
        style={{
          gridTemplateColumns: `repeat(${cols}, 1fr)`,
          gridTemplateRows: `repeat(${rows}, 1fr)`,
        }}
      >
        {slots.map((cam, i) => {
          if (!cam) return (
            <div key={`empty-${i}`} className="camera-card empty">
              <div className="video-container">
                <div className="stream-placeholder">Слот {i + 1}</div>
              </div>
            </div>
          );

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
                    style={{ width: "100%", height: "100%", border: "none", pointerEvents: "none" }}
                    allow="autoplay; fullscreen"
                  />
                ) : (
                  <div className="stream-placeholder">Немає stream path</div>
                )}
              </div>
              <div className="camera-label">
                <span className={`status-dot ${cam.status}`}></span>
                {cam.name || `Камера ${cam.id}`}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}