import { useState } from "react";
import CameraTile from "./CameraTile";
import "./Monitoring.scss";
import { 
    useGetZonesQuery, 
    useAddZoneMutation, 
    useDeleteZoneMutation 
} from "../../services/zonesApi"; 

import cam1Video from "../../../cameras/cam1.mp4";
import cam2Video from "../../../cameras/cam2.mp4";

export default function Monitoring() {
    const [selectedCameras, setSelectedCameras] = useState([
        { id: "1", name: "Камера 1", src: cam1Video },
        { id: "2", name: "Камера 2", src: cam2Video }
    ]);

    const [activeId, setActiveId] = useState(null);
    const [focusedId, setFocusedId] = useState(null);
    const [isPanelOpen, setIsPanelOpen] = useState(false);
    const [isZoneMenuOpen, setIsZoneMenuOpen] = useState(false);

    const [mode, setMode] = useState("view");
    const [currentZone, setCurrentZone] = useState([]);
    const [selectedZoneId, setSelectedZoneId] = useState(null);

    const [zoneForm, setZoneForm] = useState({
        name: "",
        zone_type: "danger",
        risk_weight: "",
        max_people_allowed: ""
    });

    const { data: activeZones = [] } = useGetZonesQuery(activeId, { skip: !activeId });
    const [addZone] = useAddZoneMutation();
    const [deleteZone] = useDeleteZoneMutation();

    const resetDrawState = () => {
        setMode("view");
        setCurrentZone([]);
        setZoneForm({ name: "", zone_type: "danger", risk_weight: "", max_people_allowed: "" });
        setIsZoneMenuOpen(false);
    };

    const handleSaveZone = async () => {
        if (currentZone.length < 3) return;
        const payload = {
            name: zoneForm.name || `Зона ${activeZones.length + 1}`,
            camera_id: activeId,
            polygon: currentZone.map(([x, y]) => [Math.round(x), Math.round(y)]),
            zone_type: zoneForm.zone_type,
            risk_weight: Number(zoneForm.risk_weight || 40),
            max_people_allowed: Number(zoneForm.max_people_allowed || 0),
            is_active: true
        };
        try {
            await addZone(payload).unwrap();
            resetDrawState();
        } catch (e) { console.error(e); }
    };

    const getGridClass = () => {
        if (focusedId) return "focused-mode";
        return selectedCameras.length === 2 ? "grid-2" : "grid-4";
    };

    return (
        <div className={`monitoring-container ${isPanelOpen ? "panel-open" : "panel-closed"}`}>
            <div className="main-content">
                <main className={`camera-grid ${getGridClass()}`}>
                    {selectedCameras.map(cam => (
                        <CameraTile
                            key={cam.id}
                            camera={cam}
                            isPanelOpen={isPanelOpen}
                            isActive={activeId === cam.id}
                            isFocused={focusedId === cam.id}
                            isZoneMenuOpen={isZoneMenuOpen}
                            currentDrawingPoints={activeId === cam.id ? currentZone : []}
                            mode={mode}
                            editingZoneId={null}
                            onSelect={(id) => {
                                if (mode === "draw") return;
                                setActiveId(prev => prev === id ? null : id);
                                resetDrawState();
                            }}
                            onDoubleClick={(id) => {
                                if (mode === "draw") return;
                                setFocusedId(prev => prev === id ? null : id)}
                            }
                            onPointAdd={(p) => mode === "draw" && setCurrentZone(prev => [...prev, p])}
                        />
                    ))}
                </main>

                <div className="sidebar-trigger">
                    <button className="burger-btn" onClick={() => setIsPanelOpen(!isPanelOpen)}>
                        {isPanelOpen ? "✕" : "☰"}
                    </button>
                </div>
            </div>

            <aside className={`control-panel ${isPanelOpen ? "visible" : ""}`}>
                <h2>Керування</h2>
                <button className="start-btn">Почати моніторинг</button>

                {activeId ? (
                    <div className="panel-content">
                        <p style={{color: "#94a3b8", marginBottom: "10px"}}>Камера: <strong style={{color: "white"}}>{activeId}</strong></p>
                        <button className="zone-btn" onClick={() => setIsZoneMenuOpen(!isZoneMenuOpen)}>
                            {isZoneMenuOpen ? "Сховати зони" : "Управління зонами"}
                        </button>

                        {isZoneMenuOpen && (
                            <div className="zones-manager" style={{marginTop: "20px"}}>
                                {mode === "view" ? (
                                    <button className="zone-btn" onClick={() => setMode("draw")}>+ Додати нову зону</button>
                                ) : (
                                    <div className="draw-actions">
                                        <div className="zone-form">
                                            <input type="text" placeholder="Назва" value={zoneForm.name} onChange={e => setZoneForm({...zoneForm, name: e.target.value})} />
                                            <select value={zoneForm.zone_type} onChange={e => setZoneForm({...zoneForm, zone_type: e.target.value})}>
                                                <option value="danger">Danger</option>
                                                <option value="warning">Warning</option>
                                                <option value="safe">Safe</option>
                                            </select>
                                            <input type="text" placeholder="Risk (0-100)" value={zoneForm.risk_weight} onChange={e => setZoneForm({...zoneForm, risk_weight: e.target.value})} />
                                            <input type="text" placeholder="Max people" value={zoneForm.max_people_allowed} onChange={e => setZoneForm({...zoneForm, max_people_allowed: e.target.value})} />
                                        </div>
                                        <button className="zone-btn" onClick={handleSaveZone}>Зберегти</button>
                                        <button className="zone-btn" onClick={resetDrawState} style={{background: "#475569"}}>Скасувати</button>
                                    </div>
                                )}

                                <div className="zones-list">
                                    {activeZones.map(z => (
                                        <div key={z.id} className="zone-item">
                                            <strong style={{color: "white"}}>{z.name}</strong>
                                            <button onClick={() => setSelectedZoneId(z.id)} style={{background: "none", border: "none", color: "#ef4444", cursor: "pointer", fontSize: "16px"}}>🗑</button>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}
                    </div>
                ) : (
                    <p style={{marginTop: "20px", color: "#64748b"}}>Виберіть камеру</p>
                )}

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
                        <p style={{marginBottom: "20px"}}>Видалити зону?</p>
                        <div style={{display: "flex", gap: "10px"}}>
                            <button className="delete-btn" onClick={async () => { await deleteZone(selectedZoneId); setSelectedZoneId(null); }}>Видалити</button>
                            <button onClick={() => setSelectedZoneId(null)} style={{flex: 1, padding: "10px", borderRadius: "6px", background: "#475569", color: "white", border: "none", cursor: "pointer"}}>Скасувати</button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}