import { useNavigate } from "react-router-dom";
import "./CamerasGrid.scss";

import cam1Video from "../../../cameras/cam1.mp4";
import cam2Video from "../../../cameras/cam2.mp4";

export default function CamerasGrid() {
  const navigate = useNavigate();

  const cameras = [
    { id: 1, name: "Camera 1", src: cam1Video },
    { id: 2, name: "Camera 2", src: cam2Video },
  ];

  return (
    <div className="cameras-page">
      
      <div className="grid">
        {cameras.map((cam) => (
          <div
            key={cam.id}
            className="camera-card"
            onClick={() => navigate(`/monitoring/${cam.id}`)}
          >
            <video
              src={cam.src}
              autoPlay
              loop
              muted
              playsInline
              style={{ width: "100%", height: "100%", objectFit: "cover", borderRadius: "8px" }}
            />
            <div className="camera-label">{cam.name}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
