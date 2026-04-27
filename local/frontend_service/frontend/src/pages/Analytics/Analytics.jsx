import { useMemo, useState, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import { useEventStream } from "../../hooks/useEventStream";
import { useGetCamerasQuery } from "../../services/camerasApi";
import {
    BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
    PieChart, Pie, Cell, LineChart, Line, CartesianGrid, Legend
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
                        cursor={{ fill: "rgba(255, 255, 255, 0.05)" }}
                    />
                    <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                        {data.map((entry, i) => (
                            <Cell key={i} fill={entry.color} />
                        ))}
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
                    <Pie
                        data={data}
                        dataKey="count"
                        nameKey="name"
                        cx="50%"
                        cy="50%"
                        outerRadius={80}
                        innerRadius={45}
                        paddingAngle={3}
                    >
                        {data.map((_, i) => (
                            <Cell key={i} fill={COLORS[i % COLORS.length]} />
                        ))}
                    </Pie>
                    <Tooltip
                        contentStyle={{ background: "#1e293b", border: "1px solid #334155", borderRadius: 8, color: "white" }}
                    />
                    <Legend
                        iconType="circle"
                        iconSize={8}
                        wrapperStyle={{ fontSize: 11, color: "#64748b" }}
                    />
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
                                    <div
                                        className="zone-rank-fill"
                                        style={{ width: `${(zone.count / max) * 100}%` }}
                                    />
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

function EventsTimeline({ events, timeRange }) {
    const data = useMemo(() => {
        const buckets = {};
        const now = Date.now();
        const step = timeRange <= 60 ? 1 : 5;
        const bucketCount = Math.ceil(timeRange / step);

        for (let i = bucketCount - 1; i >= 0; i--) {
            const t = new Date(now - i * step * 60000);
            const key = `${t.getHours().toString().padStart(2, "0")}:${t.getMinutes().toString().padStart(2, "0")}`;
            buckets[key] = { time: key, critical: 0, high: 0, medium: 0, low: 0 };
        }

        events.forEach(e => {
            const d = new Date(e.timestamp);
            const roundedMinutes = Math.floor(d.getMinutes() / step) * step;
            const key = `${d.getHours().toString().padStart(2, "0")}:${roundedMinutes.toString().padStart(2, "0")}`;
            if (buckets[key] && e.risk_level) buckets[key][e.risk_level]++;
        });

        return Object.values(buckets);
    }, [events, timeRange]);

    const label = timeRange < 60 ? `Last ${timeRange} min` : `Last ${timeRange / 60}h`;

    return (
        <div className="chart-card wide">
            <h3>Events Timeline — {label}</h3>
            <ResponsiveContainer width="100%" height={200}>
                <LineChart data={data}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                    <XAxis
                        dataKey="time"
                        tick={{ fill: "#64748b", fontSize: 10 }}
                        axisLine={false}
                        tickLine={false}
                        interval={timeRange <= 30 ? 4 : timeRange <= 60 ? 9 : 11}
                    />
                    <YAxis tick={{ fill: "#64748b", fontSize: 10 }} axisLine={false} tickLine={false} />
                    <Tooltip
                        contentStyle={{ background: "#1e293b", border: "1px solid #334155", borderRadius: 8, color: "white" }}
                    />
                    <Legend wrapperStyle={{ fontSize: 11, color: "#64748b" }} />
                    {RISK_ORDER.map(r => (
                        <Line
                            key={r}
                            type="monotone"
                            dataKey={r}
                            stroke={RISK_COLORS[r]}
                            strokeWidth={2}
                            dot={false}
                            name={r.toUpperCase()}
                        />
                    ))}
                </LineChart>
            </ResponsiveContainer>
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
    const [timeRange, setTimeRange] = useState(30);

    useEffect(() => {
        const cam = searchParams.get("camera");
        if (cam) setCameraFilter(cam);
    }, [searchParams]);

    const filteredEvents = useMemo(() => {
        if (cameraFilter === "all") return events;
        return events.filter(e => String(e.camera_id) === String(cameraFilter));
    }, [events, cameraFilter]);

    const criticalCount = filteredEvents.filter(e => e.risk_level === "critical").length;
    const highCount = filteredEvents.filter(e => e.risk_level === "high").length;
    const uniqueZones = new Set(filteredEvents.map(e => e.zone_name).filter(Boolean)).size;
    const runningCameras = cameras.filter(c => c.status === "running").length;

    return (
        <div className="analytics-page">
            <div className="analytics-header">
                <div>
                    <h1>Analytics</h1>
                    <p>Real-time security event analysis</p>
                </div>
                <div className="analytics-controls">
                    <select
                        className="camera-filter"
                        value={cameraFilter}
                        onChange={e => setCameraFilter(e.target.value)}
                    >
                        <option value="all">All cameras</option>
                        {cameras.map(c => (
                            <option key={c.id} value={String(c.id)}>
                                {c.name || `Camera ${c.id}`}
                            </option>
                        ))}
                    </select>
                    <select
                        className="camera-filter"
                        value={timeRange}
                        onChange={e => setTimeRange(Number(e.target.value))}
                    >
                        <option value={15}>Last 15 min</option>
                        <option value={30}>Last 30 min</option>
                        <option value={60}>Last 1 hour</option>
                        <option value={360}>Last 6 hours</option>
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
                <EventsTimeline events={filteredEvents} timeRange={timeRange} />
            </div>
        </div>
    );
}