import { useNavigate } from "react-router-dom";
import "./CamerasGrid.scss";

export default function CamerasGrid() {

    const navigate = useNavigate();

    const cameras = [
        { id: 1, name: "Camera 1" },
        { id: 2, name: "Camera 2" }
    ];

    return (
        <div className="cameras-page">

            <div className="top-bar">
                <h1>Камери</h1>
            </div>

            <div className="grid">

                {cameras.map(cam => (
                    <div
                        key={cam.id}
                        className="camera-card"
                        onClick={() => navigate(`/monitoring/${cam.id}`)}
                    >
                        <img
                            src={`http://127.0.0.1:8000/video/stream/${cam.id}`}
                            alt={cam.name}
                        />
                        <div className="camera-label">
                            {cam.name}
                        </div>
                    </div>
                ))}

            </div>

        </div>
    );
}
