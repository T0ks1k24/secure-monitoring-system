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
import { useEventStream } from "../../hooks/useEventStream";
import { useKioskMode } from "../../hooks/useKioskMode";
import { useRole } from "../../hooks/useRole";

const MEDIA_MTX_WEBRTC_URL = (import.meta.env.VITE_MEDIA_MTX_WEBRTC_URL || "http://localhost:8889").replace(/\/+$/, "");

function getStreamPath(rtsp) {
    if (!rtsp || typeof rtsp !== "string") return "";
    return rtsp.split("/").filter(Boolean).at(-1) || "";
}

function eventMatchesCamera(eventCameraId, camera) {
    const candidates = [String(camera.id), camera.streamPath, `camera${camera.id}`].filter(Boolean);
    return candidates.includes(String(eventCameraId));
}

const InfoIcon = ({ text }) => (
    <span className="info-tooltip" data-tooltip={text}>?</span>
);

const RISK_CONFIG = {
    critical: { color: "#ef4444", bg: "rgba(239,68,68,0.1)",  label: "CRITICAL" },
    high:     { color: "#f97316", bg: "rgba(249,115,22,0.1)", label: "HIGH"     },
    medium:   { color: "#eab308", bg: "rgba(234,179,8,0.1)",  label: "MEDIUM"   },
    low:      { color: "#22c55e", bg: "rgba(34,197,94,0.1)",  label: "LOW"      },
};

function EventCard({ event }) {
    const risk = RISK_CONFIG[event.risk_level] || RISK_CONFIG[event.risk] || RISK_CONFIG.medium;
    const time = new Date(event.timestamp).toLocaleTimeString("uk-UA", {
        hour: "2-digit", minute: "2-digit", second: "2-digit"
    });

    return (
        <div className="event-card" style={{ borderLeftColor: risk.color, background: risk.bg }}>
            <div className="event-card-header">
                <div className="event-card-left">
                    <span className="event-risk-badge" style={{ background: risk.color }}>
                        {risk.label}
                    </span>
                    <span className="event-type">{event.event_type.replace(/_/g, " ")}</span>
                </div>
                <span className="event-time">{time}</span>
            </div>
            <div className="event-card-body">
                {event.zone_name && (
                    <div className="event-detail">
                        <span className="event-detail-label">Zone</span>
                        <span className="event-detail-value">{event.zone_name}</span>
                    </div>
                )}
                {event.object_class && (
                    <div className="event-detail">
                        <span className="event-detail-label">Object</span>
                        <span className="event-detail-value">{event.object_class}</span>
                    </div>
                )}
                {event.confidence != null && (
                    <div className="event-detail">
                        <span className="event-detail-label">Confidence</span>
                        <span className="event-detail-value">{Math.round(event.confidence * 100)}%</span>
                    </div>
                )}
                {event.track_id != null && (
                    <div className="event-detail">
                        <span className="event-detail-label">Track ID</span>
                        <span className="event-detail-value">#{event.track_id}</span>
                    </div>
                )}
            </div>
        </div>
    );
}

export default function Monitoring() {
    const { cameraId } = useParams();
    const { data: cameras = [] } = useGetCamerasQuery();
    const { events, status: eventsStatus } = useEventStream();
    const { isKiosk, showExitBtn, setShowExitBtn, exitKiosk } = useKioskMode();
    const { isAdmin } = useRole();

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
    const [expandedZoneId, setExpandedZoneId] = useState(null);
    const [riskFilter, setRiskFilter] = useState("all");
    const [isRedrawing, setIsRedrawing] = useState(false);

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

    const resetDrawState = () => {
        setMode("view");
        setEditingZoneId(null);
        setCurrentZone([]);
        setIsRedrawing(false);
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
        if (isRedrawing && currentZone.length < 3) return;
        if (!isEdit && currentZone.length < 3) return;

        const canvas = document.querySelector(".camera-tile canvas");
        if (!canvas) return;
        const { width, height } = canvas;

        const pointsToSave = (isEdit && !isRedrawing)
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

    const visibleEvents = events
        .filter(evt => camera ? eventMatchesCamera(evt.camera_id, camera) : true)
        .filter(evt => riskFilter === "all" || evt.risk_level === riskFilter);

    if (!camera) return <div className="loading">Loading camera...</div>;

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
                        isRedrawing={isRedrawing}
                        onPointAdd={(p) => {
                            if (mode === "draw" || (mode === "edit" && isRedrawing)) {
                                setCurrentZone(prev => [...prev, p]);
                            }
                        }}
                    />
                </main>

                <div className="sidebar-trigger">
                    <button className="burger-btn" onClick={() => setIsPanelOpen(!isPanelOpen)}>
                        {isPanelOpen ? "✕" : "☰"}
                    </button>
                </div>
            </div>

            <aside className={`control-panel ${isPanelOpen ? "visible" : ""}`}>
                <h2>Control panel</h2>

                <div className="system-health">
                    <div>Camera: <strong>{camera.name}</strong></div>
                    <div>Status: <strong>{camera.status}</strong></div>
                </div>

                <button className="zone-btn" onClick={() => { setIsZoneMenuOpen(!isZoneMenuOpen); resetDrawState(); }}>
                    {isZoneMenuOpen ? "Hide zones" : isAdmin ? "Manage zones" : "View zones"}
                </button>

                {isZoneMenuOpen && (
                    <div className="zones-manager">
                        {mode === "view" ? (
                            <>
                                {isAdmin && (
                                    <button className="zone-btn" onClick={() => setMode("draw")}>+ Add new zone</button>
                                )}
                                {activeZones.length > 0 && (
                                    <div className="zones-list">
                                        <h3>Existing zones:</h3>
                                        <ul>
                                            {activeZones.map(zone => (
                                                <li key={zone.id} className={`zone-item ${expandedZoneId === zone.id ? "expanded" : ""}`}>
                                                    <div className="zone-item-header" onClick={() => setExpandedZoneId(prev => prev === zone.id ? null : zone.id)}>
                                                        <div className="zone-item-main">
                                                            <div className="zone-item-title">
                                                                <strong>{zone.name}</strong>
                                                                <span className={`zone-type-badge zone-type-${zone.zone_type}`}>{zone.zone_type}</span>
                                                            </div>
                                                            <div className="zone-item-meta">
                                                                <span>Risk: {zone.risk_weight}</span>
                                                                <span>Max: {zone.max_people_allowed} people</span>
                                                            </div>
                                                        </div>
                                                        <div className="zone-item-actions" onClick={e => e.stopPropagation()}>
                                                            {isAdmin && <>
                                                                <button className="edit-mini" onClick={() => {
                                                                    setMode("edit");
                                                                    setEditingZoneId(zone.id);
                                                                    setExpandedZoneId(null);
                                                                    setIsRedrawing(false);
                                                                    setCurrentZone([]);
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
                                                            </>}
                                                            <span className="zone-expand-arrow">{expandedZoneId === zone.id ? "▴" : "▾"}</span>
                                                        </div>
                                                    </div>

                                                    {expandedZoneId === zone.id && (
                                                        <div className="zone-item-details">
                                                            <div className="zone-detail-row">
                                                                <span className="zone-detail-label">Base mode</span>
                                                                <span className={`zone-mode-badge ${zone.base_mode === "RELAXED" ? "relaxed" : "strict"}`}>{zone.base_mode || "STRICT"}</span>
                                                            </div>
                                                            <div className="zone-detail-row">
                                                                <span className="zone-detail-label">Cooldown</span>
                                                                <span className="zone-detail-value">{zone.cooldown_seconds ?? 5}s</span>
                                                            </div>
                                                            <div className="zone-detail-row">
                                                                <span className="zone-detail-label">Risk multipliers</span>
                                                                <span className="zone-detail-value">relaxed: {zone.risk_multipliers?.relaxed ?? 0.3} / strict: {zone.risk_multipliers?.strict ?? 1.5}</span>
                                                            </div>
                                                            <div className="zone-detail-row">
                                                                <span className="zone-detail-label">People thresholds</span>
                                                                <span className="zone-detail-value">medium: {zone.people_thresholds?.medium ?? 2} / high: {zone.people_thresholds?.high ?? 5}</span>
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
                                        <label>Zone type <InfoIcon text="Zone behavior type." /></label>
                                        <select value={zoneForm.zone_type} onChange={e => setZoneForm({ ...zoneForm, zone_type: e.target.value })}>
                                            <option value="restricted">Danger (restricted)</option>
                                            <option value="perimeter">Warning (perimeter)</option>
                                            <option value="safe_zone">Safe (safe zone)</option>
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

                                    {mode === "edit" && (
                                        <button
                                            type="button"
                                            className="redraw-btn"
                                            onClick={() => {
                                                setIsRedrawing(true);
                                                setCurrentZone([]);
                                            }}
                                        >
                                            {isRedrawing ? "✎ Drawing new polygon..." : "↺ Redraw zone polygon"}
                                        </button>
                                    )}

                                    <button type="button" className="advanced-toggle"
                                        onClick={() => setZoneForm({ ...zoneForm, _showAdvanced: !zoneForm._showAdvanced })}>
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
                                                <label className="group-label">Risk multipliers <InfoIcon text="Risk score growth multipliers per mode." /></label>
                                                <div className="zone-field-row">
                                                    <div className="zone-field">
                                                        <label>Relaxed</label>
                                                        <input type="text" placeholder="0.3" value={zoneForm.risk_multipliers_relaxed}
                                                            onChange={e => setZoneForm({ ...zoneForm, risk_multipliers_relaxed: e.target.value })} />
                                                    </div>
                                                    <div className="zone-field">
                                                        <label>Strict</label>
                                                        <input type="text" placeholder="1.5" value={zoneForm.risk_multipliers_strict}
                                                            onChange={e => setZoneForm({ ...zoneForm, risk_multipliers_strict: e.target.value })} />
                                                    </div>
                                                </div>
                                            </div>
                                            <div className="zone-field-group">
                                                <label className="group-label">People thresholds <InfoIcon text="Crowd level thresholds used in RELAXED mode." /></label>
                                                <div className="zone-field-row">
                                                    <div className="zone-field">
                                                        <label>Medium</label>
                                                        <input type="text" placeholder="2" value={zoneForm.people_thresholds_medium}
                                                            onChange={e => setZoneForm({ ...zoneForm, people_thresholds_medium: e.target.value })} />
                                                    </div>
                                                    <div className="zone-field">
                                                        <label>High</label>
                                                        <input type="text" placeholder="5" value={zoneForm.people_thresholds_high}
                                                            onChange={e => setZoneForm({ ...zoneForm, people_thresholds_high: e.target.value })} />
                                                    </div>
                                                </div>
                                            </div>
                                            <div className="zone-field">
                                                <label>Decay per second <InfoIcon text="How fast the risk score decreases per second when no people are detected." /></label>
                                                <input type="text" placeholder="default: 1.0" value={zoneForm.decay_per_second}
                                                    onChange={e => setZoneForm({ ...zoneForm, decay_per_second: e.target.value })} />
                                            </div>
                                            <div className="zone-field">
                                                <label>Time windows <InfoIcon text="RELAXED mode time intervals in HH:MM format." /></label>
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
                                                            onClick={() => setZoneForm({ ...zoneForm, time_windows: zoneForm.time_windows.filter((_, i) => i !== idx) })}>✕</button>
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
                    <div className="events-block">
                        <div className="events-header">
                            <h3>Events</h3>
                            <div className={`ws-status ws-${eventsStatus}`}>
                                <span className="ws-dot" />
                                {eventsStatus}
                            </div>
                        </div>
                        <div className="events-filter">
                            {["all", "critical", "high", "medium", "low"].map(r => (
                                <button
                                    key={r}
                                    className={`filter-btn ${riskFilter === r ? "active" : ""}`}
                                    onClick={() => setRiskFilter(r)}
                                >
                                    {r === "all" ? "All" : r.toUpperCase()}
                                </button>
                            ))}
                        </div>
                        <div className="events-scroll">
                            {visibleEvents.length === 0 ? (
                                <div className="events-empty">No events yet</div>
                            ) : (
                                visibleEvents.map(event => (
                                    <EventCard key={`${event.id}-${event.timestamp}`} event={event} />
                                ))
                            )}
                        </div>
                    </div>
                )}
            </aside>

            {selectedZoneId && (
                <div className="modal-overlay">
                    <div className="modal-box">
                        <p>Are you sure you want to delete this zone?</p>
                        <div className="modal-actions">
                            <button className="delete-btn" onClick={async () => { await deleteZone(selectedZoneId); setSelectedZoneId(null); }}>Delete</button>
                            <button className="zone-btn" style={{ background: "#475569" }} onClick={() => setSelectedZoneId(null)}>Cancel</button>
                        </div>
                    </div>
                </div>
            )}

            {isKiosk && (
                <div className="kiosk-exit-zone"
                    onMouseEnter={() => setShowExitBtn(true)}
                    onMouseLeave={() => setShowExitBtn(false)}>
                    {showExitBtn && (
                        <button onClick={exitKiosk}>✕</button>
                    )}
                </div>
            )}
        </div>
    );
}