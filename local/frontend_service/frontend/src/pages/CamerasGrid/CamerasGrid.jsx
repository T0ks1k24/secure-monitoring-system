import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { useGetCamerasQuery } from "../../services/camerasApi";
import { getItem } from "../../utils/windowStorage";
import { useEventStream } from "../../hooks/useEventStream";
import { useKioskMode } from "../../hooks/useKioskMode";
import { useWebRTCPreload } from "../../context/WebRTCPreloadContext";
import "./CamerasGrid.scss";

const WEBRTC_BASE = (import.meta.env.VITE_MEDIA_MTX_WEBRTC_URL || "http://localhost:8889").replace(/\/+$/, "");

const getStreamPath = (rtsp) => {
    if (!rtsp || typeof rtsp !== "string") return "";
    return rtsp.split("/").filter(Boolean).at(-1) || "";
};

const DEFAULT_SLOT_COUNT = 9;

const getGridLayout = (count) => {
    if (count === 4)  return { cols: 2, rows: 2 };
    if (count === 6)  return { cols: 3, rows: 2 };
    if (count === 9)  return { cols: 3, rows: 3 };
    if (count === 12) return { cols: 4, rows: 3 };
    if (count === 16) return { cols: 4, rows: 4 };
    return { cols: 3, rows: 3 };
};

const RISK_CONFIG = {
    critical: { color: "#ef4444", label: "CRITICAL" },
    high:     { color: "#f97316", label: "HIGH" },
    medium:   { color: "#eab308", label: "MEDIUM" },
    low:      { color: "#22c55e", label: "LOW" },
};

/**
 * Замінник iframe-елемента в сітці камер.
 * Повідомляє WebRTCPreloadProvider про своє DOM-місце — provider
 * позиціонує preload-iframe поверх цього div через position:fixed.
 * При розмонтуванні (навігація на іншу сторінку) iframe залишається
 * в DOM і WebRTC-з'єднання не переривається.
 */
function VideoSlot({ streamUrl }) {
    const { attachCamera, detachCamera } = useWebRTCPreload();
    const ref = useRef(null);

    useEffect(() => {
        if (!streamUrl || !ref.current) return;
        attachCamera(streamUrl, ref.current);
        return () => detachCamera(streamUrl);
    }, [streamUrl, attachCamera, detachCamera]);

    return (
        <div
            ref={ref}
            style={{ width: "100%", height: "100%", background: "transparent" }}
        />
    );
}

function useAlerts(events) {
    const [alerts, setAlerts] = useState({});
    const timersRef = useRef({});

    useEffect(() => {
        if (!events.length) return;
        const latest = events[0];
        const camId = latest.camera_id;

        if (timersRef.current[camId]) clearTimeout(timersRef.current[camId]);

        setAlerts(prev => ({
            ...prev,
            [camId]: latest,
        }));
        timersRef.current[camId] = setTimeout(() => {
            setAlerts(prev => {
                const next = { ...prev };
                delete next[camId];
                return next;
            });
        }, 8000);
    }, [events[0]?.id]);

    const dismiss = (camId) => {
        if (timersRef.current[camId]) clearTimeout(timersRef.current[camId]);
        setAlerts(prev => {
            const next = { ...prev };
            delete next[camId];
            return next;
        });
    };

    return { alerts, dismiss };
}

export default function CamerasGrid() {
    const navigate = useNavigate();
    const { data: cameras = [], isLoading } = useGetCamerasQuery();
    const { events } = useEventStream();
    const { alerts, dismiss } = useAlerts(events);
    const { isKiosk, showExitBtn, setShowExitBtn, exitKiosk } = useKioskMode();

    const [slotCount, setSlotCount] = useState(DEFAULT_SLOT_COUNT);
    const [slotConfig, setSlotConfig] = useState([]);

    useEffect(() => {
        const init = async () => {
            const count = parseInt(await getItem("grid_slot_count") || String(DEFAULT_SLOT_COUNT));
            setSlotCount(count);
            try {
                const saved = await getItem("slot_config");
                if (!saved) { setSlotConfig(Array(count).fill(null)); return; }
                const parsed = JSON.parse(saved);
                const result = Array(count).fill(null);
                parsed.forEach((id, i) => { if (i < count) result[i] = id; });
                setSlotConfig(result);
            } catch {
                setSlotConfig(Array(count).fill(null));
            }
        };
        init();
    }, []);

    const { cols, rows } = getGridLayout(slotCount);
    const slots = slotConfig.map(id =>
        id ? cameras.find(c => String(c.id) === String(id)) || null : null
    );

    if (isLoading) return <div className="loading">Loading cameras...</div>;

    return (
        <div className="cameras-page">
            <div className="grid" style={{
                gridTemplateColumns: `repeat(${cols}, 1fr)`,
                gridTemplateRows: `repeat(${rows}, 1fr)`,
            }}>
                {slots.map((cam, i) => {
                    if (!cam) return (
                        <div key={`empty-${i}`} className="camera-card empty">
                            <div className="video-container">
                                <div className="stream-placeholder">Slot {i + 1}</div>
                            </div>
                        </div>
                    );

                    const streamPath = getStreamPath(cam.rtsp);
                    const streamUrl = streamPath ? `${WEBRTC_BASE}/${streamPath}` : "";
                    const alert = alerts[String(cam.id)];
                    const risk = alert ? RISK_CONFIG[alert.risk_level] || RISK_CONFIG.medium : null;

                    return (
                        <div
                            key={cam.id}
                            className={`camera-card ${alert ? "has-alert" : ""}`}
                            style={alert ? { "--alert-color": risk.color } : {}}
                            onClick={() => { dismiss(String(cam.id)); navigate(`/monitoring/${cam.id}`); }}
                        >
                            <div className="video-container">
                                {streamUrl ? (
                                    <VideoSlot streamUrl={streamUrl} />
                                ) : (
                                    <div className="stream-placeholder">No stream available</div>
                                )}
                            </div>

                            {alert && (
                                <div className="alert-badge" style={{ background: risk.color }}>
                                    <span className="alert-badge-risk">{risk.label}</span>
                                    <span className="alert-badge-type">{alert.event_type.replace(/_/g, " ")}</span>
                                    {alert.zone_name && <span className="alert-badge-zone">{alert.zone_name}</span>}
                                    <button
                                        className="alert-dismiss"
                                        onClick={e => { e.stopPropagation(); dismiss(String(cam.id)); }}
                                    >✕</button>
                                </div>
                            )}

                            <div className="camera-label">
                                <span className={`status-dot ${cam.status}`}></span>
                                {cam.name || `Camera ${cam.id}`}
                                {alert && <span className="label-alert-dot" style={{ background: risk.color }} />}
                            </div>
                        </div>
                    );
                })}
            </div>
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