import { useRef, useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import "./Monitoring.scss";

import cam1Video from "../../../cameras/cam1.mp4";
import cam2Video from "../../../cameras/cam2.mp4";

const videoMap = {
    "1": cam1Video,
    "2": cam2Video
};

export default function Monitoring() {
    const canvasRef = useRef(null);
    const videoRef = useRef(null);
    const { cameraId } = useParams();

    const [mode, setMode] = useState("view");
    const [zones, setZones] = useState([]);
    const [currentZone, setCurrentZone] = useState([]);
    
    const [isZoneMenuOpen, setIsZoneMenuOpen] = useState(false);

    const [zoneForm, setZoneForm] = useState({
        name: "",
        zone_type: "danger",
        risk_weight: "",
        max_people_allowed: ""
    });

    const [selectedZoneId, setSelectedZoneId] = useState(null);
    const [editingZoneId, setEditingZoneId] = useState(null);

    const resetZoneForm = () => {
        setZoneForm({
            name: "",
            zone_type: "danger",
            risk_weight: "",
            max_people_allowed: ""
        });
    };

    const resetDrawState = () => {
        setMode("view");
        setEditingZoneId(null);
        setCurrentZone([]);
        resetZoneForm();
    };

    const loadZones = async () => {
        try {
            const res = await fetch(`http://127.0.0.1:8000/zones/${cameraId}`);
            if (!res.ok) throw new Error("Fetch failed");
            const data = await res.json();

            const mapped = data.map(zone => ({
                id: zone.id,
                name: zone.name,
                type: zone.zone_type,
                risk_weight: zone.risk_weight,
                max_people_allowed: zone.max_people_allowed,
                points: zone.polygon || []
            }));

            setZones(mapped);
        } catch (error) {
            console.error("Помилка завантаження:", error);
        }
    };

    const handleDeleteZone = async () => {
        if (selectedZoneId === null) return;
        
        try {
            const response = await fetch(`http://127.0.0.1:8000/zones/${selectedZoneId}`, {
                method: "DELETE"
            });

            if (response.ok) {
                resetDrawState();
                await loadZones();
            }

            setSelectedZoneId(null);
        } catch (error) {
            console.error("Помилка видалення:", error);
            setSelectedZoneId(null);
        }
    };

    const handleSaveZone = async () => {
        const isEdit = mode === "edit";
        
        if (!isEdit && currentZone.length < 3) return;

        const url = isEdit 
            ? `http://127.0.0.1:8000/zones/${editingZoneId}` 
            : "http://127.0.0.1:8000/zones/";
        
        const method = isEdit ? "PUT" : "POST";

        const existingZone = isEdit ? zones.find(z => z.id === editingZoneId) : null;

        const payload = {
            name: zoneForm.name || `Zone ${zones.length + 1}`,
            camera_id: cameraId,
            polygon: isEdit ? existingZone.points : currentZone.map(([x, y]) => [Math.round(x), Math.round(y)]),
            zone_type: zoneForm.zone_type || "danger",
            risk_weight: Number(zoneForm.risk_weight || 40),
            max_people_allowed: Number(zoneForm.max_people_allowed || 0),
            is_active: true
        };

        try {
            const response = await fetch(url, {
                method: method,
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });

            if (response.ok) {
                resetDrawState();
                loadZones();
            }
        } catch (error) {
            console.error("Помилка збереження:", error);
        }
    };

    useEffect(() => {
        loadZones();
    }, [cameraId]);

    useEffect(() => {
        const canvas = canvasRef.current;
        const video = videoRef.current;

        if (!canvas || !video) return;

        const resizeCanvas = () => {
            const newWidth = video.clientWidth;
            const newHeight = video.clientHeight;

            if (!newWidth || !newHeight) return;

            canvas.width = newWidth;
            canvas.height = newHeight;
        };

        video.addEventListener("loadedmetadata", resizeCanvas);
        window.addEventListener("resize", resizeCanvas);

        resizeCanvas();

        return () => {
            video.removeEventListener("loadedmetadata", resizeCanvas);
            window.removeEventListener("resize", resizeCanvas);
        };
    }, [cameraId]);

    const getCenterOfPolygon = (points) => {
        if (!points || points.length === 0) return { x: 0, y: 0 };

        const sumX = points.reduce((acc, point) => acc + point[0], 0);
        const sumY = points.reduce((acc, point) => acc + point[1], 0);

        return {
            x: sumX / points.length,
            y: sumY / points.length
        };
    };

    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;
        const ctx = canvas.getContext("2d");
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        zones.forEach(zone => {
            if (!zone.points || zone.points.length < 2) return;

            if (mode === "edit") {
                ctx.globalAlpha = zone.id === editingZoneId ? 1.0 : 0.4;
                ctx.lineWidth = zone.id === editingZoneId ? 4 : 2;
            } else {
                ctx.globalAlpha = 1.0;
                ctx.lineWidth = 2;
            }

            let color;
            switch (zone.type) {
                case "danger": color = "red"; break;
                case "warning": color = "yellow"; break;
                case "safe": color = "limegreen"; break;
                default: color = "gray";
            }

            ctx.beginPath();
            ctx.moveTo(zone.points[0][0], zone.points[0][1]);
            for (let i = 1; i < zone.points.length; i++) {
                ctx.lineTo(zone.points[i][0], zone.points[i][1]);
            }
            if (zone.points.length > 2) ctx.closePath();
            ctx.strokeStyle = color;
            ctx.stroke();

            zone.points.forEach(([x, y]) => {
                ctx.beginPath();
                ctx.arc(x, y, 4, 0, Math.PI * 2);
                ctx.fillStyle = color;
                ctx.fill();
            });

            if (isZoneMenuOpen) {
                const center = getCenterOfPolygon(zone.points);
                ctx.font = "bold 16px sans-serif";
                ctx.fillStyle = "white";
                ctx.textAlign = "center";
                ctx.textBaseline = "middle";
                ctx.shadowColor = "black";
                ctx.shadowBlur = 4;
                ctx.shadowOffsetX = 1;
                ctx.shadowOffsetY = 1;
                ctx.fillText(zone.name, center.x, center.y);
                ctx.shadowBlur = 0;
                ctx.shadowOffsetX = 0;
                ctx.shadowOffsetY = 0;
            }
        });

        ctx.globalAlpha = 1.0;

        if (currentZone.length > 0) {
            ctx.beginPath();
            ctx.moveTo(currentZone[0][0], currentZone[0][1]);
            for (let i = 1; i < currentZone.length; i++) {
                ctx.lineTo(currentZone[i][0], currentZone[i][1]);
            }
            if (currentZone.length > 2) ctx.closePath();
            ctx.strokeStyle = "red";
            ctx.lineWidth = 2;
            ctx.stroke();
            currentZone.forEach(([x, y]) => {
                ctx.beginPath();
                ctx.arc(x, y, 5, 0, Math.PI * 2);
                ctx.fillStyle = "red";
                ctx.fill();
            });
        }
    }, [zones, currentZone, isZoneMenuOpen, mode, editingZoneId]);

    const handleCanvasClick = (e) => {
        if (mode !== "draw") return;

        const canvas = canvasRef.current;
        const rect = canvas.getBoundingClientRect();

        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;

        setCurrentZone(prev => [...prev, [x, y]]);
    };

    return (
        <>
            <div className="container">
                <div className="video-wrapper">
                    <div className="video-inner">
                        <video
                            ref={videoRef}
                            src={videoMap[cameraId]}
                            autoPlay
                            loop
                            muted
                            playsInline
                            style={{ width: "100%", height: "auto", display: "block" }}
                        />
                        <canvas
                            ref={canvasRef}
                            onClick={handleCanvasClick}
                            style={{
                                pointerEvents: mode === "draw" ? "auto" : "none"
                            }}
                        ></canvas>
                    </div>
                </div>

                <div className="control-panel">
                    <h2>Керування</h2>

                    <button className="start-btn">
                        Почати моніторинг
                    </button>

                    <button 
                        className="zone-btn"
                        onClick={() => {
                            setIsZoneMenuOpen(prev => !prev);
                        }}
                        style={{ marginTop: "15px", backgroundColor: isZoneMenuOpen ? "#475569" : "" }}
                    >
                        {isZoneMenuOpen ? "Сховати зони" : "Управління зонами"}
                    </button>
                    {isZoneMenuOpen && (
                        <div className="zones-manager" style={{ marginTop: "20px" }}>
                            
                            {mode === "view" && (
                                <button
                                    className="zone-btn"
                                    onClick={() => {
                                        resetZoneForm();
                                        setCurrentZone([]);
                                        setMode("draw");
                                    }}
                                >
                                    + Додати нову зону
                                </button>
                            )}

                            {(mode === "draw" || mode === "edit") && (
                                <div className="draw-actions">

                                    <div className="zone-form">

                                        <input
                                            type="text"
                                            placeholder="Назва зони"
                                            value={zoneForm.name}
                                            onChange={(e) =>
                                                setZoneForm({ ...zoneForm, name: e.target.value })
                                            }
                                        />

                                        <select
                                            value={zoneForm.zone_type}
                                            onChange={(e) =>
                                                setZoneForm({ ...zoneForm, zone_type: e.target.value })
                                            }
                                        >
                                            <option value="danger">Danger</option>
                                            <option value="warning">Warning</option>
                                            <option value="safe">Safe</option>
                                        </select>

                                        <input
                                            type="text"
                                            min="0"
                                            max="100"
                                            placeholder="Risk level (0-100)"
                                            value={zoneForm.risk_weight}
                                            onChange={(e) => {
                                                const value = e.target.value;

                                                if (value === "" || (/^\d+$/.test(value) && Number(value) <= 100)) {
                                                    setZoneForm({ ...zoneForm, risk_weight: value });
                                                }
                                            }}
                                        />

                                        <input
                                            type="text"
                                            min="0"
                                            placeholder="Max people"
                                            value={zoneForm.max_people_allowed}
                                            onChange={(e) => {
                                                const value = e.target.value;

                                                if (value === "" || /^\d+$/.test(value)) {
                                                    setZoneForm({ ...zoneForm, max_people_allowed: value });
                                                }
                                            }}
                                        />

                                    </div>

                                    <button className="zone-btn" onClick={handleSaveZone}>
                                        {mode === "edit" ? "Зберегти зміни" : "Зберегти"}
                                    </button>

                                    <button className="zone-btn" onClick={resetDrawState}>
                                        Скасувати
                                    </button>
                                </div>
                            )}
                            {mode === "view" && zones.length > 0 && (
                                <div className="zones-list">
                                    <h3>Існуючі зони:</h3>
                                    <ul>
                                        {zones.map(zone => (
                                            <li key={zone.id} className="zone-item">
                                                <div className="zone-header">
                                                    <strong>{zone.name}</strong>
                                                    <span className="zone-risk">Ризик: {zone.risk_weight || 40}</span>
                                                </div>
                                                <div className="zone-actions">
                                                    <button 
                                                        className="edit-btn"
                                                        onClick={() => {
                                                            setMode("edit");
                                                            setEditingZoneId(zone.id);
                                                            setZoneForm({
                                                                name: zone.name,
                                                                zone_type: zone.type,
                                                                risk_weight: String(zone.risk_weight),
                                                                max_people_allowed: String(zone.max_people_allowed || 0)
                                                            });
                                                        }}
                                                    >
                                                        ✎ Редаг.
                                                    </button>
                                                    <button 
                                                        className="delete-btn"
                                                        onClick={() => setSelectedZoneId(zone.id)}
                                                    >
                                                        🗑 Видалити
                                                    </button>
                                                </div>
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                            )}
                        </div>
                    )}

                    {!isZoneMenuOpen && (
                        <div className="events-block" style={{ marginTop: "20px" }}>
                            <h3>Події</h3>
                            <ul id="events"></ul>
                        </div>
                    )}

                </div>
            </div>
            {selectedZoneId !== null && (
                <div className="modal-overlay">
                    <div className="modal-box">
                        <p>Ви впевнені що хочете видалити цю зону?</p>

                        <div className="modal-actions">
                            <button className="delete-btn" onClick={handleDeleteZone}>
                                Так, видалити
                            </button>

                            <button className="zone-btn" onClick={() => setSelectedZoneId(null)}>
                                Скасувати
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </>
    );
}