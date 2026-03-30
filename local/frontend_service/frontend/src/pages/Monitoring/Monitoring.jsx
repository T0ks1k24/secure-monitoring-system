import { useState } from "react";
import CameraTile from "./CameraTile";
import CameraSelectionModal from "./CameraSelectionModal";
import "./Monitoring.scss";
import { 
    useGetZonesQuery, 
    useAddZoneMutation,
    useUpdateZoneMutation, 
    useDeleteZoneMutation 
} from "../../services/zonesApi"; 

import cam1Video from "../../../cameras/cam1.mp4";
import cam2Video from "../../../cameras/cam2.mp4";

const ALL_CAMERAS = [
    { id: "1", name: "Камера 1", src: cam1Video },
    { id: "2", name: "Камера 2", src: cam2Video },
    { id: "3", name: "Камера 3", src: cam1Video },
    { id: "4", name: "Камера 4", src: cam2Video },
    { id: "5", name: "Камера 5", src: cam1Video },
    { id: "6", name: "Камера 6", src: cam2Video },
    { id: "7", name: "Камера 7", src: cam1Video },
    { id: "8", name: "Камера 8", src: cam2Video },
    { id: "9", name: "Камера 9", src: cam1Video },
    { id: "10", name: "Камера 10", src: cam2Video },
];

export default function Monitoring() {
    const [selectedCameras, setSelectedCameras] = useState(ALL_CAMERAS.slice(0, 2));
    const [activeId, setActiveId] = useState(null);
    const [focusedId, setFocusedId] = useState(null);
    const [isPanelOpen, setIsPanelOpen] = useState(false);
    const [isZoneMenuOpen, setIsZoneMenuOpen] = useState(false);
    const [isModalOpen, setIsModalOpen] = useState(false);

    const [mode, setMode] = useState("view");
    const [currentZone, setCurrentZone] = useState([]);
    const [selectedZoneId, setSelectedZoneId] = useState(null);
    const [editingZoneId, setEditingZoneId] = useState(null);

    const [zoneForm, setZoneForm] = useState({
        name: "",
        zone_type: "danger",
        risk_weight: "",
        max_people_allowed: ""
    });

    const { data: activeZones = [] } = useGetZonesQuery(activeId, { skip: !activeId });
    const [addZone] = useAddZoneMutation();
    const [deleteZone] = useDeleteZoneMutation();
    const [updateZone] = useUpdateZoneMutation();

    const resetDrawState = () => {
        setMode("view");
        setEditingZoneId(null);
        setCurrentZone([]);
        setZoneForm({ name: "", zone_type: "danger", risk_weight: "", max_people_allowed: "" });
    };

    const handleSaveZone = async () => {
        const isEdit = mode === "edit";
        if (!isEdit && currentZone.length < 3) return;

        const canvas = document.querySelector('.camera-tile.active canvas');
        if (!canvas) return;

        const { width, height } = canvas;

        const pointsToSave = isEdit
            ? activeZones.find(z => z.id === editingZoneId)?.points
            : currentZone.map(([x, y]) => [x / width, y / height]);

        const payload = {
            name: zoneForm.name || `Зона ${activeZones.length + 1}`,
            camera_id: activeId,
            polygon: pointsToSave,
            zone_type: zoneForm.zone_type,
            risk_weight: Number(zoneForm.risk_weight || 40),
            max_people_allowed: Number(zoneForm.max_people_allowed || 0),
            is_active: true
        };

        try {
            if (isEdit) {
                await updateZone({ id: editingZoneId, ...payload }).unwrap();
            } else {
                await addZone(payload).unwrap();
            }
            resetDrawState();
        } catch (e) { console.error(e); }
    };

    const handleSaveCameras = (newSelection) => {
        setSelectedCameras(newSelection);
        setIsModalOpen(false);
        setActiveId(null);
        setFocusedId(null);
    };

    const getGridClass = () => {
        if (focusedId) return "focused-mode";
        if (selectedCameras.length === 1) return "grid-1";
        if (selectedCameras.length === 2) return "grid-2";
        if (selectedCameras.length === 3) return "grid-3";
        return "grid-4";
    };

    const getTileProps = (cam) => ({
        key: cam.id,
        camera: cam,
        isPanelOpen,
        isActive: activeId === cam.id,
        isFocused: focusedId === cam.id,
        isZoneMenuOpen,
        currentDrawingPoints: activeId === cam.id ? currentZone : [],
        mode,
        editingZoneId,
        onSelect: (id) => { if (mode !== "view") return; setActiveId(prev => prev === id ? null : id); resetDrawState(); },
        onDoubleClick: (id) => { if (mode !== "view" || selectedCameras.length === 1) return; setFocusedId(prev => prev === id ? null : id); },
        onPointAdd: (p) => mode === "draw" && setCurrentZone(prev => [...prev, p]),
    });

    return (
        <div className={`monitoring-container ${isPanelOpen ? "panel-open" : "panel-closed"}`}>
            <div className="main-content">
                <main className={`camera-grid ${getGridClass()}`}>
                    {focusedId ? (
                        <>
                            {selectedCameras.find(cam => cam.id === focusedId) && (
                                <CameraTile
                                    {...getTileProps(selectedCameras.find(cam => cam.id === focusedId))}
                                    isFocused={true}
                                />
                            )}
                            <div className="side-cameras">
                                {selectedCameras
                                    .filter(cam => cam.id !== focusedId)
                                    .map(cam => <CameraTile key={cam.id} {...getTileProps(cam)} isFocused={false} />)
                                }
                            </div>
                        </>
                    ) : (
                        selectedCameras.map(cam => <CameraTile key={cam.id} {...getTileProps(cam)} />)
                    )}
                </main>

                <div className="sidebar-trigger">
                    <button className="burger-btn" onClick={() => setIsPanelOpen(!isPanelOpen)}>
                        {isPanelOpen ? "✕" : "☰"}
                    </button>
                </div>
            </div>

            <aside className={`control-panel ${isPanelOpen ? "visible" : ""}`}>
                <h2>Керування</h2>
                <button className="start-btn" onClick={() => setIsModalOpen(true)}>+ Налаштувати камери</button>
                <button className="start-btn">Почати моніторинг</button>

                {activeId ? (
                    <div className="panel-content">
                        <p style={{color: "#94a3b8", marginBottom: "10px"}}>Камера: <strong style={{color: "white"}}>{activeId}</strong></p>
                        <button className="zone-btn" onClick={() => { setIsZoneMenuOpen(!isZoneMenuOpen); resetDrawState(); }}>
                            {isZoneMenuOpen ? "Сховати зони" : "Управління зонами"}
                        </button>

                        {isZoneMenuOpen && (
                            <div className="zones-manager">
                                {mode === "view" ? (
                                    <>
                                        <button className="zone-btn" onClick={() => setMode("draw")}>+ Додати нову зону</button>
                                        {activeZones.length > 0 && (
                                            <div className="zones-list">
                                                <h3>Існуючі зони:</h3>
                                                <ul>
                                                    {activeZones.map(zone => (
                                                        <li key={zone.id} className="zone-item">
                                                            <div className="zone-info">
                                                                <strong>{zone.name}</strong>
                                                                <span>Ризик: {zone.risk_weight}</span>
                                                            </div>
                                                            <div className="zone-actions">
                                                                <button className="edit-mini" onClick={() => {
                                                                    setMode("edit");
                                                                    setEditingZoneId(zone.id);
                                                                    setZoneForm({
                                                                        name: zone.name,
                                                                        zone_type: zone.type,
                                                                        risk_weight: String(zone.risk_weight),
                                                                        max_people_allowed: String(zone.max_people_allowed)
                                                                    });
                                                                }}>✎</button>
                                                                <button className="delete-mini" onClick={() => setSelectedZoneId(zone.id)}>🗑</button>
                                                            </div>
                                                        </li>
                                                    ))}
                                                </ul>
                                            </div>
                                        )}
                                    </>
                                ) : (
                                    <div className="draw-actions">
                                        <div className="zone-form">
                                            <input type="text" placeholder="Назва" value={zoneForm.name} onChange={e => setZoneForm({...zoneForm, name: e.target.value})} />
                                            <select value={zoneForm.zone_type} onChange={e => setZoneForm({...zoneForm, zone_type: e.target.value})}>
                                                <option value="danger">Danger</option>
                                                <option value="warning">Warning</option>
                                                <option value="safe">Safe</option>
                                            </select>
                                            <input type="text" placeholder="Ризик" value={zoneForm.risk_weight} onChange={e => setZoneForm({...zoneForm, risk_weight: e.target.value})} />
                                            <input type="text" placeholder="Макс. людей" value={zoneForm.max_people_allowed} onChange={e => setZoneForm({...zoneForm, max_people_allowed: e.target.value})} />
                                        </div>
                                        <button className="zone-btn" onClick={handleSaveZone}>{mode === "edit" ? "Зберегти зміни" : "Зберегти"}</button>
                                        <button className="zone-btn" style={{background: "#475569"}} onClick={resetDrawState}>Скасувати</button>
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                ) : <p style={{marginTop: "20px", color: "#64748b"}}>Виберіть камеру</p>}

                {!isZoneMenuOpen && (
                    <div className="events-block" style={{marginTop: "20px"}}>
                        <h3 style={{color: "white", fontSize: "16px", marginBottom: "10px"}}>Події</h3>
                        <ul id="events"></ul>
                    </div>
                )}
            </aside>

            {selectedZoneId && (
                <div className="modal-overlay">
                    <div className="modal-box">
                        <p>Ви впевнені, що хочете видалити цю зону?</p>
                        <div className="modal-actions">
                            <button className="delete-btn" onClick={async () => { await deleteZone(selectedZoneId); setSelectedZoneId(null); }}>Видалити</button>
                            <button className="zone-btn" style={{background: "#475569"}} onClick={() => setSelectedZoneId(null)}>Скасувати</button>
                        </div>
                    </div>
                </div>
            )}
            
            {isModalOpen && (
                <CameraSelectionModal
                    allCameras={ALL_CAMERAS}
                    selectedCameras={selectedCameras}
                    onClose={() => setIsModalOpen(false)}
                    onSave={handleSaveCameras}
                />
            )}
        </div>
    );
}