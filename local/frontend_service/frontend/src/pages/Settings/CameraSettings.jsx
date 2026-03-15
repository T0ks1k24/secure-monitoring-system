import { useGetCamerasQuery, useStartCameraMutation, useStopCameraMutation, useDeleteCameraMutation } from "../../services/camerasApi";
import "./CameraSettings.scss";

export default function CameraSettings() {
  const { data: cameras = [], isLoading } = useGetCamerasQuery();
  const [startCamera] = useStartCameraMutation();
  const [stopCamera] = useStopCameraMutation();
  const [deleteCamera] = useDeleteCameraMutation();

  return (
    <div className="settings-container">
      <div className="header">
        <h2>Налаштування системних камер</h2>
        <button className="add-btn">+ Додати камеру</button>
      </div>

      <table className="settings-table">
        <thead>
          <tr>
            <th>Статус</th>
            <th>ID / Назва</th>
            <th>RTSP Адреса</th>
            <th>Параметри (FPS/Q)</th>
            <th>Статистика</th>
            <th>Дії</th>
          </tr>
        </thead>
        <tbody>
          {cameras.map(cam => (
            <tr key={cam.id}>
              <td><span className={`status-pill ${cam.status}`}>{cam.status}</span></td>
              <td>
                <div className="cam-id">{cam.id}</div>
                <div className="cam-name">{cam.name || "Без назви"}</div>
              </td>
              <td className="rtsp-text">{cam.rtsp}</td>
              <td>{cam.fps} FPS / {cam.jpeg_quality}%</td>
              <td className="stats">
                <div>Sent: {cam.frames_sent}</div>
                <div className={cam.motion_active ? "active" : ""}>Events: {cam.motion_events}</div>
              </td>
              <td className="actions">
                {cam.status === 'stopped' ? 
                  <button onClick={() => startCamera(cam.id)} title="Запустити">▶</button> : 
                  <button onClick={() => stopCamera(cam.id)} title="Зупинити">⏹</button>
                }
                <button onClick={() => {}}>✎</button>
                <button className="delete" onClick={() => deleteCamera(cam.id)}>🗑</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}