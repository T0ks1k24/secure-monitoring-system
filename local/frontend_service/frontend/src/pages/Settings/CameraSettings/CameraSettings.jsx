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
  const [expandedId, setExpandedId] = useState(null);

  const openModalForCreate = () => { setCameraToEdit(null); setIsModalOpen(true); };
  const openModalForEdit = (cam) => { setCameraToEdit(cam); setIsModalOpen(true); };

  const handleSaveCamera = async (data) => {
    try {
      if (cameraToEdit) {
        await updateCamera({ id: cameraToEdit.id, ...data }).unwrap();
      } else {
        await addCamera(data).unwrap();
      }
      setIsModalOpen(false);
    } catch (err) {
      alert("Помилка: " + (err?.data?.detail || "Не вдалося зберегти"));
    }
  };

  if (isLoading) return <div className="loading">Завантаження...</div>;

  return (
    <div className="settings-container">
      <div className="cam-header">
        <h2>Camera Management</h2>
        <button className="add-btn" onClick={openModalForCreate}>+ Add camera</button>
      </div>

      <div className="cam-list">
        {cameras.length === 0 && (
          <div className="cam-empty">No cameras added yet. Click "+ Add camera" to get started.</div>
        )}
        {cameras.map(cam => (
          <div key={cam.id} className={`cam-card ${expandedId === cam.id ? "expanded" : ""}`}>

            <div className="cam-card-main" onClick={() => setExpandedId(prev => prev === cam.id ? null : cam.id)}>
              <div className="cam-card-left">
                <span className={`status-pill ${cam.status}`}>{cam.status}</span>
                <div className="cam-identity">
                  <strong>{cam.name || "Unnamed camera"}</strong>
                  <span className="cam-id-badge">ID: {cam.id}</span>
                </div>
              </div>

              <div className="cam-card-mid">
                <code className="cam-rtsp">{cam.rtsp}</code>
              </div>

              <div className="cam-card-stats">
                <div className="stat-chip">
                  <span className="stat-label">FPS</span>
                  <span className="stat-value">{cam.fps}</span>
                </div>
                <div className="stat-chip">
                  <span className="stat-label">Quality</span>
                  <span className="stat-value">{cam.jpeg_quality}%</span>
                </div>
                <div className="stat-chip">
                  <span className="stat-label">Sent</span>
                  <span className="stat-value">{cam.frames_sent}</span>
                </div>
                <div className={`stat-chip ${cam.motion_active ? "active" : ""}`}>
                  <span className="stat-label">Events</span>
                  <span className="stat-value">{cam.motion_events}</span>
                </div>
              </div>

              <div className="cam-card-actions" onClick={e => e.stopPropagation()}>
                {cam.status === "stopped"
                  ? <button className="action-btn start" onClick={() => startCamera(cam.id)} title="Start">▶</button>
                  : <button className="action-btn stop" onClick={() => stopCamera(cam.id)} title="Stop">⏹</button>
                }
                <button className="action-btn edit" onClick={() => openModalForEdit(cam)} title="Edit">✎</button>
                <button className="action-btn delete" onClick={() => deleteCamera(cam.id)} title="Delete">🗑</button>
                <span className="expand-arrow">{expandedId === cam.id ? "▴" : "▾"}</span>
              </div>
            </div>

            {expandedId === cam.id && (
              <div className="cam-card-details">
                <div className="details-section">
                  <h4>General</h4>
                  <div className="details-grid">
                    <div className="detail-row"><span>Resize width</span><span>{cam.resize_width}px</span></div>
                    <div className="detail-row"><span>Enabled</span><span>{cam.enabled ? "Yes" : "No"}</span></div>
                    <div className="detail-row"><span>Frames failed</span><span>{cam.frames_failed}</span></div>
                    <div className="detail-row"><span>Frames skipped</span><span>{cam.frames_skipped}</span></div>
                    <div className="detail-row"><span>Motion active</span><span className={cam.motion_active ? "text-green" : ""}>{cam.motion_active ? "Yes" : "No"}</span></div>
                  </div>
                </div>

                {cam.motion && (
                  <div className="details-section">
                    <h4>Motion detection</h4>
                    <div className="details-grid">
                      <div className="detail-row"><span>Enabled</span><span>{cam.motion.enabled ? "Yes" : "No"}</span></div>
                      <div className="detail-row"><span>Min contour area</span><span>{cam.motion.min_contour_area}</span></div>
                      <div className="detail-row"><span>Min total area</span><span>{cam.motion.min_total_area}</span></div>
                      <div className="detail-row"><span>Min solidity</span><span>{cam.motion.min_solidity}</span></div>
                      <div className="detail-row"><span>Consecutive frames</span><span>{cam.motion.min_consecutive_frames}</span></div>
                      <div className="detail-row"><span>Cooldown</span><span>{cam.motion.cooldown_seconds}s</span></div>
                      <div className="detail-row"><span>Blur size</span><span>{cam.motion.blur_size}</span></div>
                      <div className="detail-row"><span>Diff threshold</span><span>{cam.motion.diff_threshold}</span></div>
                      <div className="detail-row"><span>Dilate iterations</span><span>{cam.motion.dilate_iterations}</span></div>
                      <div className="detail-row"><span>BG update alpha</span><span>{cam.motion.background_update_alpha}</span></div>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>

      <AddCameraModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSave={handleSaveCamera}
        initialValues={cameraToEdit}
      />
    </div>
  );
}