import { useState } from "react";
import {
  useGetCamerasQuery,
  useAddCameraMutation,
  useUpdateCameraMutation,
  useStartCameraMutation,
  useStopCameraMutation,
  useDeleteCameraMutation
} from "../../../services/camerasApi";
import "./CameraSettings.scss";
import AddCameraModal from "./AddCameraModal/AddCameraModal";

export default function CameraSettings() {  
  const { data: cameras = [], isLoading } = useGetCamerasQuery();
  const [addCamera] = useAddCameraMutation();
  const [updateCamera] = useUpdateCameraMutation();
  const [startCamera] = useStartCameraMutation();
  const [stopCamera] = useStopCameraMutation();
  const [deleteCamera] = useDeleteCameraMutation();

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [cameraToEdit, setCameraToEdit] = useState(null);

  const openModalForCreate = () => {
    setCameraToEdit(null);
    setIsModalOpen(true);
  };

  const openModalForEdit = (camera) => {
    setCameraToEdit(camera); 
    setIsModalOpen(true);
  };

  const handleSaveCamera = async (cameraData) => {
    try {
      if (cameraToEdit) {
        await updateCamera({ id: cameraToEdit.id, ...cameraData }).unwrap();
      } else {
        await addCamera(cameraData).unwrap();
      }
      setIsModalOpen(false);
    } catch (error) {
      alert("Помилка: " + (error?.data?.detail || "Не вдалося зберегти зміни"));
    }
  };

  if (isLoading) return <div className="loading">Завантаження...</div>;

  return (
    <div className="settings-container">
      <div className="header">
        <h2>Налаштування системних камер</h2>
        <button className="add-btn" onClick={openModalForCreate}>
            + Додати камеру
        </button>
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
                <button title="Редагувати" onClick={() => openModalForEdit(cam)}>✎</button>
                <button className="delete" onClick={() => deleteCamera(cam.id)}>🗑</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <AddCameraModal 
        isOpen={isModalOpen} 
        onClose={() => setIsModalOpen(false)} 
        onSave={handleSaveCamera} 
        initialValues={cameraToEdit}
      />
    </div>
  );
}