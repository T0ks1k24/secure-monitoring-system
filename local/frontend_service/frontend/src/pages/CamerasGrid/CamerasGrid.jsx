import { useNavigate } from "react-router-dom";
import { useGetCamerasQuery } from "../../services/camerasApi";
import "./CamerasGrid.scss";

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
            const streamPath = cam.rtsp ? cam.rtsp.split("/").pop() : "";

            return (
              <div
                key={cam.id}
                className="camera-card"
                onClick={() => navigate(`/monitoring/${cam.id}`)}
              >
                <div className="video-container">
                    <iframe
                      src={`http://127.0.0.1:8889/${streamPath}`}
                      style={{
                        width: "100%",
                        height: "100%",
                        border: "none",
                        pointerEvents: "none",
                      }}
                      allow="autoplay; fullscreen"
                    />
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