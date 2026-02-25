import { useRef, useEffect, useState } from "react"
import { useParams } from "react-router-dom";
import "./Monitoring.scss"

import cam1Video from "../../../cameras/cam1.mp4";
import cam2Video from "../../../cameras/cam2.mp4";

const videoMap = {
    "1": cam1Video,
    "2": cam2Video
};

export default function Monitoring(){

    const canvasRef = useRef(null);
    const videoRef = useRef(null);
    const {cameraId} = useParams();

    const [mode, setMode] = useState("view");
    const [zones, setZones] = useState([]);
    const [currentZone, setCurrentZone] = useState([]);
    const [canvasSize, setCanvasSize] = useState({ width: 0, height: 0 });

    const loadZones = async () => {
        const res = await fetch(`http://127.0.0.1:8000/zones/${cameraId}`);
        const data = await res.json();

        const mapped = data.map(zone => ({
            id: zone.id,
            name: zone.name,
            type: zone.zone_type,
            points: zone.polygon || []
        }));

        setZones(mapped);
    };

    useEffect(() => {
        loadZones();
    }, [cameraId]);

    useEffect(() => {
        const canvas = canvasRef.current;
        const video = videoRef.current;

        if (!canvas || !video) return;

        const resizeCanvas = () => {
            canvas.width = video.clientWidth;
            canvas.height = video.clientHeight;
            setCanvasSize({ width: canvas.width, height: canvas.height });
        };

        if (video.readyState >= 1) { 
            resizeCanvas();
        } else {
            video.onloadedmetadata = resizeCanvas;
        }

        window.addEventListener("resize", resizeCanvas);

        return () => window.removeEventListener("resize", resizeCanvas);
    }, [cameraId]);

    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;

        const ctx = canvas.getContext("2d");
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        ctx.lineWidth = 2;

        zones.forEach(zone => {

            if (!zone.points || zone.points.length < 2) return;

            const color = zone.type === "danger" ? "red" : "yellow";

            ctx.beginPath();
            ctx.moveTo(zone.points[0][0], zone.points[0][1]);

            for (let i = 1; i < zone.points.length; i++) {
                ctx.lineTo(zone.points[i][0], zone.points[i][1]);
            }

            if (zone.points.length > 2) {
                ctx.closePath();
            }

            ctx.strokeStyle = color;
            ctx.stroke();

            zone.points.forEach(([x, y]) => {
                ctx.beginPath();
                ctx.arc(x, y, 4, 0, Math.PI * 2);
                ctx.fillStyle = color;
                ctx.fill();
            });
        });

        if (currentZone.length > 0) {

            ctx.beginPath();
            ctx.moveTo(currentZone[0][0], currentZone[0][1]);

            for (let i = 1; i < currentZone.length; i++) {
                ctx.lineTo(currentZone[i][0], currentZone[i][1]);
            }

            if (currentZone.length > 2) {
                ctx.closePath();
            }

            ctx.strokeStyle = "red";
            ctx.stroke();

            currentZone.forEach(([x, y]) => {
                ctx.beginPath();
                ctx.arc(x, y, 5, 0, Math.PI * 2);
                ctx.fillStyle = "red";
                ctx.fill();
            });
        }

    }, [zones, currentZone, canvasSize]);

    const handleCanvasClick = (e) => {
        if (mode !== "draw") return;

        const canvas = canvasRef.current;
        const rect = canvas.getBoundingClientRect();

        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;

        setCurrentZone(prev => [...prev, [x, y]]);
    };


    return(
        <>
            <div className="top-bar">
                <h1>Події безпеки</h1>

                <div className="risk">
                    Рівень ризику:{" "}
                    <span className="risk-low">LOW</span>
                </div>
            </div>

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

                {/* CONTROL PANEL */}
                <div className="control-panel">
                    <h2>Керування</h2>

                    <button className="start-btn">
                        Почати моніторинг
                    </button>

                    {mode === "view" && (
                        <button
                            className="zone-btn"
                            onClick={() => {
                                setCurrentZone([]);
                                setMode("draw");
                            }}
                        >
                            Додати зону
                        </button>
                    )}

                    {mode === "draw" && (
                        <>

                            <button
                                className="zone-btn"
                                onClick={async () => {
                                    if (currentZone.length < 3) return;

                                    await fetch("http://127.0.0.1:8000/zones/", {
                                        method: "POST",
                                        headers: {
                                            "Content-Type": "application/json"
                                        },
                                        body: JSON.stringify({
                                            name: `Zone ${zones.length + 1}`,
                                            camera_id: cameraId,
                                            polygon: currentZone.map(([x, y]) => [Math.round(x), Math.round(y)]),
                                            zone_type: "danger",
                                            risk_weight: 40,
                                            is_active: true,
                                            max_people_allowed: 0
                                        })
                                    });

                                    setCurrentZone([]);
                                    setMode("view");

                                    loadZones();
                                }}

                            >
                                Зберегти
                            </button>
                            
                            <button
                                className="zone-btn"
                                onClick={() => { setCurrentZone([]); setMode("view")}}
                            >
                                Скасувати
                            </button>
                        </>
                    )}

                    <h3>Події</h3>
                    <ul id="events">
                        {/* сюди пізніше підключимо SSE */}
                    </ul>
                </div>
            </div>
        </>
    )
}