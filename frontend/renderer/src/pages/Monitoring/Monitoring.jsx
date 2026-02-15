import { useRef, useEffect, useState } from "react"
import "./Monitoring.scss"

export default function Monitoring(){

    const canvasRef = useRef(null);
    const imgRef = useRef(null);

    const [mode, setMode] = useState("view");
    const [zones, setZones] = useState([]);
    const [currentZone, setCurrentZone] = useState([]);

    useEffect(() => {
        const canvas = canvasRef.current;
        const img = imgRef.current;

        if (!canvas || !img) return;

        const resizeCanvas = () => {
            canvas.width = img.clientWidth;
            canvas.height = img.clientHeight;
        };

        if (img.complete) {
            resizeCanvas();
        } else {
            img.onload = resizeCanvas;
        }

        window.addEventListener("resize", resizeCanvas);

        return () => window.removeEventListener("resize", resizeCanvas);
    }, []);

    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;

        const ctx = canvas.getContext("2d");
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        ctx.lineWidth = 2;

        // 🔹 Малюємо всі збережені зони
        zones.forEach(zone => {
            if (zone.length < 2) return;

            ctx.beginPath();
            ctx.moveTo(zone[0][0], zone[0][1]);

            for (let i = 1; i < zone.length; i++) {
                ctx.lineTo(zone[i][0], zone[i][1]);
            }

            ctx.closePath();
            ctx.strokeStyle = "lime";
            ctx.stroke();

            zone.forEach(([x, y]) => {
                ctx.beginPath();
                ctx.arc(x, y, 4, 0, Math.PI * 2);
                ctx.fillStyle = "lime";
                ctx.fill();
            });
        });

        // 🔹 Малюємо поточну зону (червону)
        if (currentZone.length > 0) {
            ctx.beginPath();
            ctx.moveTo(currentZone[0][0], currentZone[0][1]);

            for (let i = 1; i < currentZone.length; i++) {
                ctx.lineTo(currentZone[i][0], currentZone[i][1]);
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

    }, [zones, currentZone]);

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
                {/* VIDEO */}
                <div className="video-wrapper">
                    <div className="video-inner">
                        <img
                            ref={imgRef}
                            src="http://127.0.0.1:8000/video/stream"
                            alt="Video stream"
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
                                onClick={() => {
                                    if (currentZone.length < 3) return;

                                    setZones(prev => [...prev, currentZone]);
                                    setCurrentZone([]);
                                    setMode("view");
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