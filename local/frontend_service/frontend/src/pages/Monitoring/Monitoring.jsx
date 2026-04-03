import { useState, useEffect, useCallback, useMemo } from "react";
import { useParams } from "react-router-dom";
import CameraTile from "./CameraTile";
import CameraSelectionModal from "./CameraSelectionModal";
import "./Monitoring.scss";
import {
    useGetZonesQuery,
    useAddZoneMutation,
    useUpdateZoneMutation,
    useDeleteZoneMutation
} from "../../services/zonesApi";
import { useGetCamerasQuery } from "../../services/camerasApi";

const API_BASE_URL = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/\/+$/, "");
const MEDIA_MTX_WEBRTC_URL = (import.meta.env.VITE_MEDIA_MTX_WEBRTC_URL || "http://localhost:8889").replace(/\/+$/, "");
const WS_EVENTS_URL =
    import.meta.env.VITE_WS_EVENTS_URL ||
    `${API_BASE_URL.startsWith("https://")
        ? API_BASE_URL.replace("https://", "wss://")
        : API_BASE_URL.replace("http://", "ws://")}/ws/events`;
const MAX_EVENTS = 50;

function normalizeEvent(raw) {
    if (!raw || typeof raw !== "object") return null;
    return {
        id: String(raw.id || `${raw.camera_id || "unknown"}-${raw.timestamp || Date.now()}`),
        camera_id: String(raw.camera_id || ""),
        event_type: raw.event_type || "unknown",
        risk: raw.risk || "unknown",
        zone_name: raw.zone_name || "",
        timestamp: raw.timestamp || new Date().toISOString(),
        metadata: raw.metadata || {},
    };
}

function getStreamPath(rtsp) {
    if (!rtsp || typeof rtsp !== "string") return "";
    const parts = rtsp.split("/").filter(Boolean);
    return parts.at(-1) || "";
}

function eventMatchesCamera(eventCameraId, camera) {
    const candidates = [
        String(camera.id),
        camera.streamPath,
        `camera${camera.id}`,
    ].filter(Boolean);
    return candidates.includes(String(eventCameraId));
}

export default function Monitoring() {
    const { cameraId } = useParams();
    const { data: cameras = [] } = useGetCamerasQuery();

    const [selectedCameras, setSelectedCameras] = useState([]);
    const [activeId, setActiveId] = useState(null);
    const [focusedId, setFocusedId] = useState(null);
    const [isPanelOpen, setIsPanelOpen] = useState(false);
    const [isZoneMenuOpen, setIsZoneMenuOpen] = useState(false);
    const [isModalOpen, setIsModalOpen] = useState(false);

    const [mode, setMode] = useState("view");
    const [currentZone, setCurrentZone] = useState([]);
    const [selectedZoneId, setSelectedZoneId] = useState(null);
    const [editingZoneId, setEditingZoneId] = useState(null);

    const [isKiosk, setIsKiosk] = useState(false);
    const [showExitBtn, setShowExitBtn] = useState(false);
    const [events, setEvents] = useState([]);
    const [eventsStatus, setEventsStatus] = useState("connecting");

    const [zoneForm, setZoneForm] = useState({
        name: "",
        zone_type: "danger",
        risk_weight: "",
        max_people_allowed: ""
    });

    const allCameras = useMemo(() => {
        return cameras.map((cam) => {
            const streamPath = getStreamPath(cam.rtsp);
            return {
                id: String(cam.id),
                name: cam.name || `Камера ${cam.id}`,
                streamPath,
                zoneCameraId: streamPath || String(cam.id),
                webrtcUrl: streamPath ? `${MEDIA_MTX_WEBRTC_URL}/${streamPath}` : "",
                status: cam.status,
            };
        });
    }, [cameras]);

    useEffect(() => {
        if (!allCameras.length) {
            setSelectedCameras([]);
            return;
        }

        setSelectedCameras((previous) => {
            const previousIds = new Set(previous.map((cam) => cam.id));
            const preserved = allCameras.filter((cam) => previousIds.has(cam.id));
            if (preserved.length > 0) return preserved;

            if (cameraId) {
                const preferred = allCameras.find((cam) => cam.id === String(cameraId));
                if (preferred) {
                    return [preferred];
                }
            }

            return allCameras.slice(0, 2);
        });
    }, [allCameras, cameraId]);

    useEffect(() => {
        if (activeId && !selectedCameras.some((cam) => cam.id === activeId)) {
            setActiveId(null);
        }
    }, [selectedCameras, activeId]);

    const activeCamera = selectedCameras.find((cam) => cam.id === activeId);
    const { data: activeZones = [] } = useGetZonesQuery(
        activeCamera?.zoneCameraId,
        { skip: !activeCamera?.zoneCameraId }
    );
    const [addZone] = useAddZoneMutation();
    const [deleteZone] = useDeleteZoneMutation();
    const [updateZone] = useUpdateZoneMutation();

    const hasWindowApi = typeof window !== "undefined" && !!window.windowAPI;

    const exitKiosk = useCallback(() => {
        if (window.windowAPI?.toggleKiosk) {
            window.windowAPI.toggleKiosk();
        }
        setIsKiosk(false);
        setShowExitBtn(false);
        document.body.classList.remove("kiosk-mode");
    }, []);

    useEffect(() => {
        if (!hasWindowApi || !window.windowAPI?.onKioskChange) return;

        window.windowAPI.onKioskChange((val) => {
            setIsKiosk(val);
            document.body.classList.toggle("kiosk-mode", val);
        });
    }, [hasWindowApi]);

    useEffect(() => {
        const handleKeyDown = (e) => {
            if (e.key === "Escape") exitKiosk();
        };
        window.addEventListener("keydown", handleKeyDown);
        return () => window.removeEventListener("keydown", handleKeyDown);
    }, [exitKiosk]);

    useEffect(() => {
        let cancelled = false;
        const loadInitialEvents = async () => {
            try {
                const response = await fetch(`${API_BASE_URL}/events/`);
                if (!response.ok) return;
                const data = await response.json();
                if (cancelled || !Array.isArray(data)) return;

                const prepared = data
                    .map(normalizeEvent)
                    .filter(Boolean)
                    .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
                    .slice(0, MAX_EVENTS);
                setEvents(prepared);
            } catch (error) {
                console.error("Failed to load initial events", error);
            }
        };

        loadInitialEvents();
        return () => {
            cancelled = true;
        };
    }, []);

    useEffect(() => {
        let socket = null;
        let reconnectTimer = null;
        let manuallyClosed = false;

        const connect = () => {
            setEventsStatus("connecting");
            socket = new WebSocket(WS_EVENTS_URL);

            socket.onopen = () => {
                setEventsStatus("connected");
            };

            socket.onmessage = (message) => {
                try {
                    const parsed = JSON.parse(message.data);
                    const incomingEvent = normalizeEvent(parsed);
                    if (!incomingEvent) return;

                    setEvents((previous) => {
                        const withoutDuplicate = previous.filter((item) => item.id !== incomingEvent.id);
                        return [incomingEvent, ...withoutDuplicate].slice(0, MAX_EVENTS);
                    });
                } catch (error) {
                    console.error("Failed to parse websocket event", error);
                }
            };

            socket.onerror = () => {
                setEventsStatus("disconnected");
                socket?.close();
            };

            socket.onclose = () => {
                if (manuallyClosed) return;
                setEventsStatus("disconnected");
                reconnectTimer = window.setTimeout(connect, 3000);
            };
        };

        connect();

        return () => {
            manuallyClosed = true;
            if (reconnectTimer) window.clearTimeout(reconnectTimer);
            if (socket && (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)) {
                socket.close();
            }
        };
    }, []);

    const resetDrawState = () => {
        setMode("view");
        setEditingZoneId(null);
        setCurrentZone([]);
        setZoneForm({ name: "", zone_type: "danger", risk_weight: "", max_people_allowed: "" });
    };

    const handleSaveZone = async () => {
        const isEdit = mode === "edit";
        if (!isEdit && currentZone.length < 3) return;

        const canvas = document.querySelector(".camera-tile.active canvas");
        if (!canvas) return;

        const { width, height } = canvas;

        const pointsToSave = isEdit
            ? activeZones.find(z => z.id === editingZoneId)?.points
            : currentZone.map(([x, y]) => [x / width, y / height]);

        const payload = {
            name: zoneForm.name || `Зона ${activeZones.length + 1}`,
            camera_id: activeCamera?.zoneCameraId || activeId,
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

    const visibleEvents = events.filter((evt) => {
        if (!activeCamera) return true;
        return eventMatchesCamera(evt.camera_id, activeCamera);
    });

    const runningCameras = cameras.filter((cam) => cam.status === "running").length;
    const connectingCameras = cameras.filter((cam) => cam.status === "connecting").length;

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

                <div className="system-health">
                    <div>Камер в системі: <strong>{cameras.length}</strong></div>
                    <div>Running: <strong>{runningCameras}</strong></div>
                    <div>Connecting: <strong>{connectingCameras}</strong></div>
                    <div>WS подій: <strong>{eventsStatus}</strong></div>
                </div>

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
                        <div className="events-status">Стан каналу: {eventsStatus}</div>
                        <ul className="events-list">
                            {visibleEvents.length === 0 ? (
                                <li className="empty">Подій поки немає</li>
                            ) : (
                                visibleEvents.map((event) => (
                                    <li key={`${event.id}-${event.timestamp}`}>
                                        [{new Date(event.timestamp).toLocaleTimeString()}]{" "}
                                        {event.event_type} | Камера: {event.camera_id} | Ризик: {event.risk}
                                        {event.zone_name ? ` | Зона: ${event.zone_name}` : ""}
                                        {event.metadata?.evidence_url ? (
                                            <a
                                                href={event.metadata.evidence_url}
                                                target="_blank"
                                                rel="noreferrer"
                                                className="event-evidence-link"
                                            >
                                                <img
                                                    src={event.metadata.evidence_url}
                                                    alt="evidence"
                                                    className="event-evidence-thumb"
                                                />
                                            </a>
                                        ) : null}
                                    </li>
                                ))
                            )}
                        </ul>
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
                    allCameras={allCameras}
                    selectedCameras={selectedCameras}
                    onClose={() => setIsModalOpen(false)}
                    onSave={handleSaveCameras}
                    activeCameraIdFromUrl={cameraId}
                />
            )}
            {isKiosk && (
                <div
                    className="kiosk-exit-zone"
                    onMouseEnter={() => setShowExitBtn(true)}
                    onMouseLeave={() => setShowExitBtn(false)}
                >
                    {showExitBtn && (
                        <button onClick={exitKiosk}>
                            ✕
                        </button>
                    )}
                </div>
            )}
        </div>
    );
}
