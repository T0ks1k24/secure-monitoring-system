import { useState, useEffect, useCallback, useMemo } from "react";
import { useParams } from "react-router-dom";
import CameraTile from "./CameraTile";
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
const InfoIcon = ({ text }) => (
    <span className="info-tooltip" data-tooltip={text}>?</span>
);
export default function Monitoring() {
    const { cameraId } = useParams();
    const { data: cameras = [] } = useGetCamerasQuery();

    const camera = useMemo(() => {
        const found = cameras.find(c => String(c.id) === String(cameraId));
        if (!found) return null;
        const streamPath = getStreamPath(found.rtsp);
        return {
            id: String(found.id),
            name: found.name || `Камера ${found.id}`,
            streamPath,
            zoneCameraId: streamPath || String(found.id),
            webrtcUrl: streamPath ? `${MEDIA_MTX_WEBRTC_URL}/${streamPath}` : "",
            status: found.status,
        };
    }, [cameras, cameraId]);

    const [isPanelOpen, setIsPanelOpen] = useState(false);
    const [isZoneMenuOpen, setIsZoneMenuOpen] = useState(false);

    const [mode, setMode] = useState("view");
    const [currentZone, setCurrentZone] = useState([]);
    const [selectedZoneId, setSelectedZoneId] = useState(null);
    const [editingZoneId, setEditingZoneId] = useState(null);

    const [isKiosk, setIsKiosk] = useState(false);
    const [showExitBtn, setShowExitBtn] = useState(false);
    const [events, setEvents] = useState([]);
    const [eventsStatus, setEventsStatus] = useState("connecting");

    const [expandedZoneId, setExpandedZoneId] = useState(null);

    const [zoneForm, setZoneForm] = useState({
        name: "",
        zone_type: "danger",
        risk_weight: "",
        max_people_allowed: "",
        base_mode: "STRICT",
        cooldown_seconds: "",
        risk_multipliers_relaxed: "",
        risk_multipliers_strict: "",
        people_thresholds_medium: "",
        people_thresholds_high: "",
        decay_per_second: "",
        time_windows: [],
        _showAdvanced: false,
    });

    const { data: activeZones = [] } = useGetZonesQuery(
        camera?.zoneCameraId,
        { skip: !camera?.zoneCameraId }
    );
    const [addZone] = useAddZoneMutation();
    const [deleteZone] = useDeleteZoneMutation();
    const [updateZone] = useUpdateZoneMutation();

    const hasWindowApi = typeof window !== "undefined" && !!window.windowAPI;

    const exitKiosk = useCallback(() => {
        if (window.windowAPI?.toggleKiosk) window.windowAPI.toggleKiosk();
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
        const handleKeyDown = (e) => { if (e.key === "Escape") exitKiosk(); };
        window.addEventListener("keydown", handleKeyDown);
        return () => window.removeEventListener("keydown", handleKeyDown);
    }, [exitKiosk]);

    useEffect(() => {
        let cancelled = false;
        const load = async () => {
            try {
                const response = await fetch(`${API_BASE_URL}/events/`);
                if (!response.ok) return;
                const data = await response.json();
                if (cancelled || !Array.isArray(data)) return;
                const prepared = data
                    .map(normalizeEvent).filter(Boolean)
                    .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))
                    .slice(0, MAX_EVENTS);
                setEvents(prepared);
            } catch (e) { console.error(e); }
        };
        load();
        return () => { cancelled = true; };
    }, []);

    useEffect(() => {
        let socket = null;
        let reconnectTimer = null;
        let manuallyClosed = false;

        const connect = () => {
            setEventsStatus("connecting");
            socket = new WebSocket(WS_EVENTS_URL);
            socket.onopen = () => setEventsStatus("connected");
            socket.onmessage = (msg) => {
                try {
                    const parsed = JSON.parse(msg.data);
                    const evt = normalizeEvent(parsed);
                    if (!evt) return;
                    setEvents(prev => {
                        const deduped = prev.filter(e => e.id !== evt.id);
                        return [evt, ...deduped].slice(0, MAX_EVENTS);
                    });
                } catch (e) { console.error(e); }
            };
            socket.onerror = () => { setEventsStatus("disconnected"); socket?.close(); };
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
        setZoneForm({
            name: "",
            zone_type: "danger",
            risk_weight: "",
            max_people_allowed: "",
            base_mode: "STRICT",
            cooldown_seconds: "",
            risk_multipliers_relaxed: "",
            risk_multipliers_strict: "",
            people_thresholds_medium: "",
            people_thresholds_high: "",
            decay_per_second: "",
            time_windows: [],
            _showAdvanced: false,
        });
    };

    const handleSaveZone = async () => {
        const isEdit = mode === "edit";
        if (!isEdit && currentZone.length < 3) return;

        const canvas = document.querySelector(".camera-tile canvas");
        if (!canvas) return;
        const { width, height } = canvas;

        const pointsToSave = isEdit
            ? activeZones.find(z => z.id === editingZoneId)?.points
            : currentZone.map(([x, y]) => [x / width, y / height]);

        const payload = {
            name: zoneForm.name || `Zone ${activeZones.length + 1}`,
            camera_id: camera?.zoneCameraId || cameraId,
            polygon: pointsToSave,
            zone_type: zoneForm.zone_type,
            risk_weight: Number(zoneForm.risk_weight || 40),
            max_people_allowed: Number(zoneForm.max_people_allowed || 0),
            is_active: true,
            base_mode: zoneForm.base_mode || "STRICT",
            cooldown_seconds: Number(zoneForm.cooldown_seconds || 5.0),
            risk_multipliers: {
                relaxed: Number(zoneForm.risk_multipliers_relaxed || 0.3),
                strict: Number(zoneForm.risk_multipliers_strict || 1.5),
            },
            people_thresholds: {
                medium: Number(zoneForm.people_thresholds_medium || 2),
                high: Number(zoneForm.people_thresholds_high || 5),
            },
            accumulation: {
                decay_per_second: Number(zoneForm.decay_per_second || 1.0),
            },
            time_windows: (zoneForm.time_windows || []).filter(tw => tw.start && tw.end),
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

    const visibleEvents = events.filter(evt =>
        camera ? eventMatchesCamera(evt.camera_id, camera) : true
    );

    if (!camera) return <div className="loading">Завантаження камери...</div>;

    return (
        <div className={`monitoring-container ${isPanelOpen ? "panel-open" : "panel-closed"}`}>
            <div className="main-content">
                <main className="camera-grid">
                    <CameraTile
                        camera={camera}
                        isPanelOpen={isPanelOpen}
                        isFocused={false}
                        isZoneMenuOpen={isZoneMenuOpen}
                        currentDrawingPoints={currentZone}
                        mode={mode}
                        editingZoneId={editingZoneId}
                        onPointAdd={(p) => mode === "draw" && setCurrentZone(prev => [...prev, p])}
                    />
                </main>

                <div className="sidebar-trigger">
                    <button className="burger-btn" onClick={() => setIsPanelOpen(!isPanelOpen)}>
                        {isPanelOpen ? "✕" : "☰"}
                    </button>
                </div>
            </div>

            <aside className={`control-panel ${isPanelOpen ? "visible" : ""}`}>
                <h2>Керування</h2>
                <div className="system-health">
                    <div>Камера: <strong>{camera.name}</strong></div>
                    <div>Статус: <strong>{camera.status}</strong></div>
                    <div>WS подій: <strong>{eventsStatus}</strong></div>
                </div>

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
                                                <li key={zone.id} className={`zone-item ${expandedZoneId === zone.id ? "expanded" : ""}`}>
                                                    <div className="zone-item-header" onClick={() => setExpandedZoneId(prev => prev === zone.id ? null : zone.id)}>
                                                        <div className="zone-item-main">
                                                            <div className="zone-item-title">
                                                                <strong>{zone.name}</strong>
                                                                <span className={`zone-type-badge zone-type-${zone.zone_type}`}>
                                                                    {zone.zone_type}
                                                                </span>
                                                            </div>
                                                            <div className="zone-item-meta">
                                                                <span>Risk: {zone.risk_weight}</span>
                                                                <span>Max: {zone.max_people_allowed} people</span>
                                                            </div>
                                                        </div>
                                                        <div className="zone-item-actions" onClick={e => e.stopPropagation()}>
                                                            <button className="edit-mini" onClick={() => {
                                                                setMode("edit");
                                                                setEditingZoneId(zone.id);
                                                                setExpandedZoneId(null);
                                                                setZoneForm({
                                                                    name: zone.name,
                                                                    zone_type: zone.zone_type,
                                                                    risk_weight: String(zone.risk_weight),
                                                                    max_people_allowed: String(zone.max_people_allowed),
                                                                    base_mode: zone.base_mode || "STRICT",
                                                                    cooldown_seconds: String(zone.cooldown_seconds || ""),
                                                                    risk_multipliers_relaxed: String(zone.risk_multipliers?.relaxed || ""),
                                                                    risk_multipliers_strict: String(zone.risk_multipliers?.strict || ""),
                                                                    people_thresholds_medium: String(zone.people_thresholds?.medium || ""),
                                                                    people_thresholds_high: String(zone.people_thresholds?.high || ""),
                                                                    decay_per_second: String(zone.accumulation?.decay_per_second || ""),
                                                                    time_windows: zone.time_windows || [],
                                                                    _showAdvanced: false,
                                                                });
                                                            }}>✎</button>
                                                            <button className="delete-mini" onClick={() => setSelectedZoneId(zone.id)}>🗑</button>
                                                            <span className="zone-expand-arrow">{expandedZoneId === zone.id ? "▴" : "▾"}</span>
                                                        </div>
                                                    </div>

                                                    {expandedZoneId === zone.id && (
                                                        <div className="zone-item-details">
                                                            <div className="zone-detail-row">
                                                                <span className="zone-detail-label">Base mode</span>
                                                                <span className={`zone-mode-badge ${zone.base_mode === "RELAXED" ? "relaxed" : "strict"}`}>
                                                                    {zone.base_mode || "STRICT"}
                                                                </span>
                                                            </div>
                                                            <div className="zone-detail-row">
                                                                <span className="zone-detail-label">Cooldown</span>
                                                                <span className="zone-detail-value">{zone.cooldown_seconds ?? 5}s</span>
                                                            </div>
                                                            <div className="zone-detail-row">
                                                                <span className="zone-detail-label">Risk multipliers</span>
                                                                <span className="zone-detail-value">
                                                                    relaxed: {zone.risk_multipliers?.relaxed ?? 0.3} / strict: {zone.risk_multipliers?.strict ?? 1.5}
                                                                </span>
                                                            </div>
                                                            <div className="zone-detail-row">
                                                                <span className="zone-detail-label">People thresholds</span>
                                                                <span className="zone-detail-value">
                                                                    medium: {zone.people_thresholds?.medium ?? 2} / high: {zone.people_thresholds?.high ?? 5}
                                                                </span>
                                                            </div>
                                                            <div className="zone-detail-row">
                                                                <span className="zone-detail-label">Decay/sec</span>
                                                                <span className="zone-detail-value">{zone.accumulation?.decay_per_second ?? 1.0}</span>
                                                            </div>
                                                            {zone.time_windows?.length > 0 && (
                                                                <div className="zone-detail-row">
                                                                    <span className="zone-detail-label">Time windows</span>
                                                                    <div className="zone-time-windows">
                                                                        {zone.time_windows.map((tw, i) => (
                                                                            <span key={i} className="zone-tw-badge">{tw.start}–{tw.end}</span>
                                                                        ))}
                                                                    </div>
                                                                </div>
                                                            )}
                                                        </div>
                                                    )}
                                                </li>
                                            ))}
                                        </ul>
                                    </div>
                                )}
                            </>
                        ) : (
                            <div className="draw-actions">
                                <div className="zone-form">

                                    <div className="zone-field">
                                        <label>Zone name <InfoIcon text="Human-readable zone name shown on canvas and in event logs." /></label>
                                        <input type="text" placeholder="e.g. Warehouse A" value={zoneForm.name}
                                            onChange={e => setZoneForm({ ...zoneForm, name: e.target.value })} />
                                    </div>

                                    <div className="zone-field">
                                        <label>Zone type <InfoIcon text="Zone behavior type. Danger=restricted access, Warning=perimeter monitoring, Safe=safe zone, Entrance=entry/exit, Parking=vehicle tracking, Pedestrian=walkway, Counting line (flow analysis)." /></label>
                                        <select value={zoneForm.zone_type} onChange={e => setZoneForm({ ...zoneForm, zone_type: e.target.value })}>
                                            <option value="restricted">Danger (restricted)</option>
                                            <option value="warning">Warning (perimeter)</option>
                                            <option value="safe">Safe (safe zone)</option>
                                            <option value="entrance">Entrance (entry/exit)</option>
                                            <option value="parking">Parking (vehicle tracking)</option>
                                            <option value="pedestrian">Pedestrian (walkway)</option>
                                            <option value="counting_line">Counting line (flow analysis)</option>
                                        </select>
                                    </div>

                                    <div className="zone-field">
                                        <label>Risk weight <InfoIcon text="Base risk weight for legacy scoring rules (0–100)." /></label>
                                        <input type="text" placeholder="0–100, default: 40" value={zoneForm.risk_weight}
                                            onChange={e => setZoneForm({ ...zoneForm, risk_weight: e.target.value })} />
                                    </div>

                                    <div className="zone-field">
                                        <label>Max people <InfoIcon text="Maximum number of people allowed in the zone simultaneously." /></label>
                                        <input type="text" placeholder="default: 0 (unlimited)" value={zoneForm.max_people_allowed}
                                            onChange={e => setZoneForm({ ...zoneForm, max_people_allowed: e.target.value })} />
                                    </div>

                                    <button
                                        type="button"
                                        className="advanced-toggle"
                                        onClick={() => setZoneForm({ ...zoneForm, _showAdvanced: !zoneForm._showAdvanced })}
                                    >
                                        Advanced settings {zoneForm._showAdvanced ? "▴" : "▾"}
                                    </button>

                                    {zoneForm._showAdvanced && (
                                        <>
                                            <div className="zone-field">
                                                <label>Base mode <InfoIcon text="Default zone mode outside time windows. STRICT applies full risk multipliers." /></label>
                                                <select value={zoneForm.base_mode} onChange={e => setZoneForm({ ...zoneForm, base_mode: e.target.value })}>
                                                    <option value="STRICT">STRICT</option>
                                                    <option value="RELAXED">RELAXED</option>
                                                </select>
                                            </div>

                                            <div className="zone-field">
                                                <label>Cooldown (sec) <InfoIcon text="Minimum pause between events from this zone (anti-spam)." /></label>
                                                <input type="text" placeholder="default: 5.0" value={zoneForm.cooldown_seconds}
                                                    onChange={e => setZoneForm({ ...zoneForm, cooldown_seconds: e.target.value })} />
                                            </div>

                                            <div className="zone-field-group">
                                                <label className="group-label">Risk multipliers <InfoIcon text="Risk score growth multipliers per mode. Relaxed=low traffic periods, Strict=full enforcement." /></label>
                                                <div className="zone-field-row">
                                                    <div className="zone-field">
                                                        <label>Relaxed</label>
                                                        <input type="text" placeholder="default: 0.3" value={zoneForm.risk_multipliers_relaxed}
                                                            onChange={e => setZoneForm({ ...zoneForm, risk_multipliers_relaxed: e.target.value })} />
                                                    </div>
                                                    <div className="zone-field">
                                                        <label>Strict</label>
                                                        <input type="text" placeholder="default: 1.5" value={zoneForm.risk_multipliers_strict}
                                                            onChange={e => setZoneForm({ ...zoneForm, risk_multipliers_strict: e.target.value })} />
                                                    </div>
                                                </div>
                                            </div>

                                            <div className="zone-field-group">
                                                <label className="group-label">People thresholds <InfoIcon text="Crowd level thresholds used in RELAXED mode to classify risk level." /></label>
                                                <div className="zone-field-row">
                                                    <div className="zone-field">
                                                        <label>Medium</label>
                                                        <input type="text" placeholder="default: 2" value={zoneForm.people_thresholds_medium}
                                                            onChange={e => setZoneForm({ ...zoneForm, people_thresholds_medium: e.target.value })} />
                                                    </div>
                                                    <div className="zone-field">
                                                        <label>High</label>
                                                        <input type="text" placeholder="default: 5" value={zoneForm.people_thresholds_high}
                                                            onChange={e => setZoneForm({ ...zoneForm, people_thresholds_high: e.target.value })} />
                                                    </div>
                                                </div>
                                            </div>

                                            <div className="zone-field">
                                                <label>Decay per second <InfoIcon text="How fast the risk score decreases per second when no people are detected in the zone." /></label>
                                                <input type="text" placeholder="default: 1.0" value={zoneForm.decay_per_second}
                                                    onChange={e => setZoneForm({ ...zoneForm, decay_per_second: e.target.value })} />
                                            </div>

                                            <div className="zone-field">
                                                <label>Time windows <InfoIcon text="RELAXED mode time intervals in HH:MM format. Outside these windows the zone runs in base mode." /></label>
                                                {(zoneForm.time_windows || []).map((tw, idx) => (
                                                    <div key={idx} className="zone-field-row" style={{ marginBottom: "6px" }}>
                                                        <input type="text" placeholder="09:00" value={tw.start}
                                                            onChange={e => {
                                                                const updated = [...zoneForm.time_windows];
                                                                updated[idx] = { ...updated[idx], start: e.target.value };
                                                                setZoneForm({ ...zoneForm, time_windows: updated });
                                                            }} />
                                                        <span style={{ color: "#64748b", alignSelf: "center" }}>—</span>
                                                        <input type="text" placeholder="10:00" value={tw.end}
                                                            onChange={e => {
                                                                const updated = [...zoneForm.time_windows];
                                                                updated[idx] = { ...updated[idx], end: e.target.value };
                                                                setZoneForm({ ...zoneForm, time_windows: updated });
                                                            }} />
                                                        <button type="button" className="tw-remove"
                                                            onClick={() => setZoneForm({ ...zoneForm, time_windows: zoneForm.time_windows.filter((_, i) => i !== idx) })}>
                                                            ✕
                                                        </button>
                                                    </div>
                                                ))}
                                                <button type="button" className="tw-add"
                                                    onClick={() => setZoneForm({ ...zoneForm, time_windows: [...(zoneForm.time_windows || []), { start: "", end: "" }] })}>
                                                    + Add interval
                                                </button>
                                            </div>
                                        </>
                                    )}
                                </div>

                                <button className="zone-btn" onClick={handleSaveZone}>{mode === "edit" ? "Save changes" : "Save"}</button>
                                <button className="zone-btn" style={{ background: "#475569" }} onClick={resetDrawState}>Cancel</button>
                            </div>
                        )}
                    </div>
                )}

                {!isZoneMenuOpen && (
                    <div className="events-block" style={{ marginTop: "20px" }}>
                        <h3 style={{ color: "white", fontSize: "16px", marginBottom: "10px" }}>Події</h3>
                        <div className="events-status">Стан каналу: {eventsStatus}</div>
                        <ul className="events-list">
                            {visibleEvents.length === 0 ? (
                                <li className="empty">Подій поки немає</li>
                            ) : (
                                visibleEvents.map(event => (
                                    <li key={`${event.id}-${event.timestamp}`}>
                                        [{new Date(event.timestamp).toLocaleTimeString()}]{" "}
                                        {event.event_type} | Ризик: {event.risk}
                                        {event.zone_name ? ` | Зона: ${event.zone_name}` : ""}
                                        {event.metadata?.evidence_url && (
                                            <a href={event.metadata.evidence_url} target="_blank" rel="noreferrer" className="event-evidence-link">
                                                <img src={event.metadata.evidence_url} alt="evidence" className="event-evidence-thumb" />
                                            </a>
                                        )}
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
                            <button className="zone-btn" style={{ background: "#475569" }} onClick={() => setSelectedZoneId(null)}>Скасувати</button>
                        </div>
                    </div>
                </div>
            )}

            {isKiosk && (
                <div
                    className="kiosk-exit-zone"
                    onMouseEnter={() => setShowExitBtn(true)}
                    onMouseLeave={() => setShowExitBtn(false)}
                >
                    {showExitBtn && (
                        <button onClick={exitKiosk}>✕ Вийти з режиму моніторингу</button>
                    )}
                </div>
            )}
        </div>
    );
}