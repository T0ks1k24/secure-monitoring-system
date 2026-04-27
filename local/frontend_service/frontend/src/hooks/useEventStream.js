import { useState, useEffect, useRef } from "react";

const API_BASE_URL = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/\/+$/, "");
const WS_EVENTS_URL = import.meta.env.VITE_WS_EVENTS_URL ||
    `${API_BASE_URL.replace(/^https/, "wss").replace(/^http/, "ws")}/ws/events`;

const MAX_EVENTS = 200;

function normalizeEvent(raw) {
    if (!raw || typeof raw !== "object") return null;
    return {
        id: String(raw.id || `${raw.camera_id}-${raw.timestamp || Date.now()}`),
        camera_id: String(raw.camera_id || ""),
        event_type: raw.event_type || "unknown",
        risk: raw.risk || "unknown",
        risk_level: (raw.risk || "unknown").toLowerCase(),
        zone_id: raw.zone_id || null,
        zone_name: raw.zone_name || "",
        object_class: raw.object_class || null,
        track_id: raw.track_id || null,
        confidence: raw.confidence ?? null,
        bbox: raw.bbox || null,
        timestamp: raw.timestamp || new Date().toISOString(),
        metadata: raw.metadata || {},
    };
}

export function useEventStream() {
    const [events, setEvents] = useState([]);
    const [status, setStatus] = useState("connecting");
    const socketRef = useRef(null);

    useEffect(() => {
        let reconnectTimer = null;
        let manuallyClosed = false;

        const connect = () => {
            setStatus("connecting");
            const socket = new WebSocket(WS_EVENTS_URL);
            socketRef.current = socket;

            socket.onopen = () => setStatus("connected");

            socket.onmessage = (msg) => {
                try {
                    const evt = normalizeEvent(JSON.parse(msg.data));
                    if (!evt) return;
                    setEvents(prev => {
                        const deduped = prev.filter(e => e.id !== evt.id);
                        return [evt, ...deduped].slice(0, MAX_EVENTS);
                    });
                } catch (e) { console.error(e); }
            };

            socket.onerror = () => { setStatus("disconnected"); socket.close(); };
            socket.onclose = () => {
                if (manuallyClosed) return;
                setStatus("disconnected");
                reconnectTimer = setTimeout(connect, 3000);
            };
        };

        fetch(`${API_BASE_URL}/events/`)
            .then(r => r.ok ? r.json() : [])
            .then(data => {
                if (!Array.isArray(data)) return;
                const prepared = data.map(normalizeEvent).filter(Boolean)
                    .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))
                    .slice(0, MAX_EVENTS);
                setEvents(prepared);
            })
            .catch(() => {});

        connect();

        return () => {
            manuallyClosed = true;
            clearTimeout(reconnectTimer);
            socketRef.current?.close();
        };
    }, []);

    return { events, status };
}