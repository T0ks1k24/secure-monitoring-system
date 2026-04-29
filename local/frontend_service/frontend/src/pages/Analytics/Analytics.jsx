import { useMemo, useState, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import { useEventStream } from "../../hooks/useEventStream";
import { useGetCamerasQuery } from "../../services/camerasApi";
import {
    BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
    PieChart, Pie, Cell, Legend
} from "recharts";
import "./Analytics.scss";

const RISK_COLORS = {
    critical: "#ef4444",
    high:     "#f97316",
    medium:   "#eab308",
    low:      "#22c55e",
};

const RISK_ORDER = ["critical", "high", "medium", "low"];

function RiskGauge({ events }) {
    const score = useMemo(() => {
        if (!events.length) return 0;
        const weights = { critical: 100, high: 60, medium: 30, low: 10 };
        const recent = events.slice(0, 20);
        const total = recent.reduce((sum, e) => sum + (weights[e.risk_level] || 0), 0);
        return Math.min(100, Math.round(total / recent.length));
    }, [events]);

    const color = score >= 75 ? "#ef4444" : score >= 50 ? "#f97316" : score >= 25 ? "#eab308" : "#22c55e";
    const label = score >= 75 ? "CRITICAL" : score >= 50 ? "HIGH" : score >= 25 ? "MEDIUM" : "LOW";

    return (
        <div className="gauge-card">
            <h3>Current Risk Level</h3>
            <div className="gauge-circle" style={{ "--color": color }}>
                <div className="gauge-inner">
                    <span className="gauge-score">{score}</span>
                    <span className="gauge-label" style={{ color }}>{label}</span>
                </div>
            </div>
            <p className="gauge-hint">Based on last {Math.min(20, events.length)} events</p>
        </div>
    );
}

function EventsByRisk({ events }) {
    const data = useMemo(() => {
        const counts = { critical: 0, high: 0, medium: 0, low: 0 };
        events.forEach(e => { if (counts[e.risk_level] !== undefined) counts[e.risk_level]++; });
        return RISK_ORDER.map(r => ({ name: r.toUpperCase(), count: counts[r], color: RISK_COLORS[r] }));
    }, [events]);

    return (
        <div className="chart-card">
            <h3>Events by Risk Level</h3>
            <ResponsiveContainer width="100%" height={200}>
                <BarChart data={data} barSize={36}>
                    <XAxis dataKey="name" tick={{ fill: "#64748b", fontSize: 11 }} axisLine={false} tickLine={false} />
                    <YAxis tick={{ fill: "#64748b", fontSize: 11 }} axisLine={false} tickLine={false} />
                    <Tooltip
                        contentStyle={{ background: "#1e293b", border: "1px solid #334155", borderRadius: 8, color: "white" }}
                        labelStyle={{ color: "#f1f5f9", fontWeight: "bold", marginBottom: "4px" }}
                        itemStyle={{ color: "#f1f5f9", fontSize: "12px" }}
                        cursor={{ fill: "rgba(255,255,255,0.05)" }}
                    />
                    <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                        {data.map((entry, i) => <Cell key={i} fill={entry.color} />)}
                    </Bar>
                </BarChart>
            </ResponsiveContainer>
        </div>
    );
}

function EventsByType({ events }) {
    const data = useMemo(() => {
        const counts = {};
        events.forEach(e => {
            const type = e.event_type.replace(/_/g, " ");
            counts[type] = (counts[type] || 0) + 1;
        });
        return Object.entries(counts)
            .sort((a, b) => b[1] - a[1])
            .slice(0, 6)
            .map(([name, count]) => ({ name, count }));
    }, [events]);

    const COLORS = ["#2563eb", "#7c3aed", "#0891b2", "#059669", "#d97706", "#dc2626"];

    return (
        <div className="chart-card">
            <h3>Events by Type</h3>
            <ResponsiveContainer width="100%" height={200}>
                <PieChart>
                    <Pie data={data} dataKey="count" nameKey="name"
                        cx="50%" cy="50%" outerRadius={80} innerRadius={45} paddingAngle={3}>
                        {data.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                    </Pie>
                    <Tooltip contentStyle={{ background: "#1e293b", border: "1px solid #334155", borderRadius: 8, color: "white" }} />
                    <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 11, color: "#64748b" }} />
                </PieChart>
            </ResponsiveContainer>
        </div>
    );
}

function TopZones({ events }) {
    const data = useMemo(() => {
        const counts = {};
        events.forEach(e => {
            if (!e.zone_name) return;
            counts[e.zone_name] = (counts[e.zone_name] || 0) + 1;
        });
        return Object.entries(counts)
            .sort((a, b) => b[1] - a[1])
            .slice(0, 5)
            .map(([name, count]) => ({ name, count }));
    }, [events]);

    if (!data.length) return (
        <div className="chart-card">
            <h3>Top Triggered Zones</h3>
            <div className="chart-empty">No zone events yet</div>
        </div>
    );

    return (
        <div className="chart-card">
            <h3>Top Triggered Zones</h3>
            <div className="zones-rank">
                {data.map((zone, i) => {
                    const max = data[0].count;
                    return (
                        <div key={zone.name} className="zone-rank-row">
                            <span className="zone-rank-num">#{i + 1}</span>
                            <div className="zone-rank-bar-wrap">
                                <span className="zone-rank-name">{zone.name}</span>
                                <div className="zone-rank-bar">
                                    <div className="zone-rank-fill" style={{ width: `${(zone.count / max) * 100}%` }} />
                                </div>
                            </div>
                            <span className="zone-rank-count">{zone.count}</span>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}

function HourlyHeatmap({ events }) {
    const hours = Array.from({ length: 24 }, (_, i) => i);

    const data = useMemo(() => {
        const total = Array(24).fill(0);
        events.forEach(e => {
            const h = new Date(e.timestamp).getHours();
            total[h]++;
        });
        return { total };
    }, [events]);

    const maxVal = Math.max(...data.total, 1);

    const getColor = (val) => {
        if (val === 0) return "#0f172a";
        const intensity = val / maxVal;
        if (intensity >= 0.75) return "#ef4444";
        if (intensity >= 0.5)  return "#f97316";
        if (intensity >= 0.25) return "#eab308";
        return "#1e3a5f";
    };

    return (
        <div className="chart-card wide">
            <h3>Activity by Hour of Day</h3>
            <div className="heatmap-wrap">
                <div className="heatmap-grid">
                    {hours.map(h => (
                        <div key={h} className="heatmap-col">
                            <div
                                className="heatmap-cell"
                                style={{ background: getColor(data.total[h]) }}
                                title={`${h}:00 — ${data.total[h]} events`}
                            >
                                {data.total[h] > 0 && (
                                    <span className="heatmap-val">{data.total[h]}</span>
                                )}
                            </div>
                            <span className="heatmap-hour">{h.toString().padStart(2, "0")}</span>
                        </div>
                    ))}
                </div>
                <div className="heatmap-legend">
                    <span>Low</span>
                    <div className="heatmap-legend-bar" />
                    <span>High</span>
                </div>
            </div>
        </div>
    );
}

function RecentEventsTable({ events, cameras }) {
    const [sortField, setSortField] = useState("timestamp");
    const [sortDir, setSortDir] = useState("desc");
    const [riskFilter, setRiskFilter] = useState("all");

    const cameraName = (id) => {
        const cam = cameras.find(c => String(c.id) === String(id));
        return cam ? (cam.name || `Camera ${cam.id}`) : String(id);
    };

    const handleSort = (field) => {
        if (sortField === field) {
            setSortDir(d => d === "asc" ? "desc" : "asc");
        } else {
            setSortField(field);
            setSortDir("desc");
        }
    };

    const sorted = useMemo(() => {
        let list = riskFilter === "all" ? [...events] : events.filter(e => e.risk_level === riskFilter);
        list.sort((a, b) => {
            let av = a[sortField] || "";
            let bv = b[sortField] || "";
            if (sortField === "timestamp") {
                av = new Date(av).getTime();
                bv = new Date(bv).getTime();
            }
            return sortDir === "asc" ? (av > bv ? 1 : -1) : (av < bv ? 1 : -1);
        });
        return list.slice(0, 200);
    }, [events, sortField, sortDir, riskFilter]);

    const exportCSV = () => {
        const headers = ["Time", "Type", "Risk", "Zone", "Object", "Confidence", "Camera", "Track ID"];

        const escape = (val) => {
            const str = String(val ?? "");
            if (str.includes(",") || str.includes('"') || str.includes("\n")) {
                return `"${str.replace(/"/g, '""')}"`;
            }
            return str;
        };

        const rows = sorted.map(e => [
            escape(new Date(e.timestamp).toLocaleString("uk-UA", {
                timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone,
                day: "2-digit",
                month: "2-digit",
                year: "numeric",
                hour: "2-digit",
                minute: "2-digit",
                second: "2-digit",
            })),
            escape(e.event_type.replace(/_/g, " ")),
            escape(e.risk_level?.toUpperCase() || "-"),
            escape(e.zone_name || "-"),
            escape(e.object_class || "-"),
            escape(e.confidence != null ? `${Math.round(e.confidence * 100)}%` : "-"),
            escape(cameraName(e.camera_id)),
            escape(e.track_id != null ? `#${e.track_id}` : "-"),
        ]);

        const csvContent = [
            headers.map(escape).join(";"),
            ...rows.map(r => r.join(";")),
        ].join("\r\n");

        const BOM = "\uFEFF";
        const blob = new Blob([BOM + csvContent], { type: "text/csv;charset=utf-8;" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `security_events_${new Date().toISOString().slice(0, 10)}.csv`;
        a.click();
        URL.revokeObjectURL(url);
    };

    const SortIcon = ({ field }) => {
        if (sortField !== field) return <span className="sort-icon">↕</span>;
        return <span className="sort-icon active">{sortDir === "asc" ? "↑" : "↓"}</span>;
    };

    return (
        <div className="chart-card wide">
            <div className="table-header">
                <h3>Recent Events</h3>
                <div className="table-controls">
                    <div className="risk-tabs">
                        {["all", ...RISK_ORDER].map(r => (
                            <button
                                key={r}
                                className={`risk-tab ${riskFilter === r ? "active" : ""}`}
                                style={riskFilter === r && r !== "all" ? {
                                    background: RISK_COLORS[r],
                                    borderColor: RISK_COLORS[r],
                                    color: "white",
                                } : {}}
                                onClick={() => setRiskFilter(r)}
                            >
                                {r === "all" ? "All" : r.toUpperCase()}
                            </button>
                        ))}
                    </div>
                    <button className="export-btn" onClick={exportCSV}>
                        <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor">
                            <path d="M8 1v9M4 7l4 4 4-4M2 13h12" stroke="currentColor" strokeWidth="1.5"
                                strokeLinecap="round" fill="none"/>
                        </svg>
                        Export CSV
                    </button>
                </div>
            </div>

            <div className="events-table-wrap">
                <table className="events-table">
                    <thead>
                        <tr>
                            <th onClick={() => handleSort("timestamp")}>Time <SortIcon field="timestamp"/></th>
                            <th onClick={() => handleSort("event_type")}>Type <SortIcon field="event_type"/></th>
                            <th onClick={() => handleSort("risk_level")}>Risk <SortIcon field="risk_level"/></th>
                            <th onClick={() => handleSort("zone_name")}>Zone <SortIcon field="zone_name"/></th>
                            <th onClick={() => handleSort("object_class")}>Object <SortIcon field="object_class"/></th>
                            <th>Confidence</th>
                            <th onClick={() => handleSort("camera_id")}>Camera <SortIcon field="camera_id"/></th>
                            <th>Track ID</th>
                        </tr>
                    </thead>
                    <tbody>
                        {sorted.length === 0 ? (
                            <tr><td colSpan={8} className="table-empty">No events</td></tr>
                        ) : (
                            sorted.map(e => (
                                <tr key={e.id}>
                                    <td className="td-time">
                                        {new Date(e.timestamp).toLocaleString("uk-UA", {
                                            timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone,
                                            day: "2-digit",
                                            month: "2-digit",
                                            year: "numeric",
                                            hour: "2-digit",
                                            minute: "2-digit",
                                            second: "2-digit",
                                        })}
                                    </td>
                                    <td className="td-type">{e.event_type.replace(/_/g, " ")}</td>
                                    <td>
                                        <span className="risk-pill" style={{
                                            background: `${RISK_COLORS[e.risk_level]}22`,
                                            color: RISK_COLORS[e.risk_level],
                                        }}>
                                            {e.risk_level?.toUpperCase()}
                                        </span>
                                    </td>
                                    <td className="td-muted">{e.zone_name || "—"}</td>
                                    <td className="td-muted">{e.object_class || "—"}</td>
                                    <td className="td-muted">
                                        {e.confidence != null ? `${Math.round(e.confidence * 100)}%` : "—"}
                                    </td>
                                    <td className="td-muted">{cameraName(e.camera_id)}</td>
                                    <td className="td-muted">
                                        {e.track_id != null ? `#${e.track_id}` : "—"}
                                    </td>
                                </tr>
                            ))
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );
}

function StatCard({ label, value, sub, color }) {
    return (
        <div className="stat-card">
            <div className="stat-value" style={{ color: color || "white" }}>{value}</div>
            <div className="stat-label">{label}</div>
            {sub && <div className="stat-sub">{sub}</div>}
        </div>
    );
}

export default function Analytics() {
    const [searchParams] = useSearchParams();
    const { events, status } = useEventStream();
    const { data: cameras = [] } = useGetCamerasQuery();

    const [cameraFilter, setCameraFilter] = useState(searchParams.get("camera") || "all");

    useEffect(() => {
        const cam = searchParams.get("camera");
        if (cam) setCameraFilter(cam);
    }, [searchParams]);

    const filteredEvents = useMemo(() => {
        if (cameraFilter === "all") return events;
        return events.filter(e => String(e.camera_id) === String(cameraFilter));
    }, [events, cameraFilter]);

    const criticalCount    = filteredEvents.filter(e => e.risk_level === "critical").length;
    const highCount        = filteredEvents.filter(e => e.risk_level === "high").length;
    const uniqueZones      = new Set(filteredEvents.map(e => e.zone_name).filter(Boolean)).size;
    const runningCameras   = cameras.filter(c => c.status === "running").length;

    return (
        <div className="analytics-page">
            <div className="analytics-header">
                <div>
                    <h1>Analytics</h1>
                    <p>Real-time security event analysis</p>
                </div>
                <div className="analytics-controls">
                    <select className="camera-filter" value={cameraFilter}
                        onChange={e => setCameraFilter(e.target.value)}>
                        <option value="all">All cameras</option>
                        {cameras.map(c => (
                            <option key={c.id} value={String(c.id)}>
                                {c.name || `Camera ${c.id}`}
                            </option>
                        ))}
                    </select>
                    <div className={`ws-status ws-${status}`}>
                        <span className="ws-dot" />
                        {status}
                    </div>
                </div>
            </div>

            <div className="stat-cards">
                <StatCard label="Total events" value={filteredEvents.length} />
                <StatCard label="Critical" value={criticalCount} color="#ef4444" sub="events" />
                <StatCard label="High risk" value={highCount} color="#f97316" sub="events" />
                <StatCard label="Active zones" value={uniqueZones} sub="triggered" />
                <StatCard label="Cameras online" value={`${runningCameras}/${cameras.length}`} color="#22c55e" />
            </div>

            <div className="analytics-grid">
                <RiskGauge events={filteredEvents} />
                <EventsByRisk events={filteredEvents} />
                <EventsByType events={filteredEvents} />
                <TopZones events={filteredEvents} />
                <HourlyHeatmap events={filteredEvents} />
                <RecentEventsTable events={filteredEvents} cameras={cameras} />
            </div>
        </div>
    );
}