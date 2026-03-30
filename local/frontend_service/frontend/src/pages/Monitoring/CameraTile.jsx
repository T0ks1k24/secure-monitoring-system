import { useRef, useEffect, useLayoutEffect, useState } from "react";
import { useGetZonesQuery } from "../../services/zonesApi";

const getCenterOfPolygon = (points) => {
    if (!points || points.length === 0) return { x: 0, y: 0 };
    const x = points.reduce((sum, p) => sum + p[0], 0) / points.length;
    const y = points.reduce((sum, p) => sum + p[1], 0) / points.length;
    return { x, y };
};

export default function CameraTile({ 
    camera, isActive, isFocused, onSelect, onDoubleClick, 
    isZoneMenuOpen, currentDrawingPoints, onPointAdd,
    mode, editingZoneId, isPanelOpen 
}) {
    const videoRef = useRef(null);
    const canvasRef = useRef(null);
    const clickTimer = useRef(null);
    const [canvasSize, setCanvasSize] = useState({ width: 0, height: 0 });
    const { data: zones = [] } = useGetZonesQuery(camera.id);

    useLayoutEffect(() => {
        const video = videoRef.current;
        const canvas = canvasRef.current;
        if (!video || !canvas) return;

        const updateSize = () => {
            const { width, height } = video.getBoundingClientRect();
            canvas.width = width;
            canvas.height = height;
            setCanvasSize({ width, height });
        };
        const resizeObserver = new ResizeObserver(() => updateSize());
        resizeObserver.observe(video);

        updateSize();

        return () => resizeObserver.disconnect();
    }, [isFocused, isPanelOpen]);

    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;
        const ctx = canvas.getContext("2d");
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        if (isActive) {
            zones.forEach(zone => {
                if (!zone.points || zone.points.length < 2) return;
                const { width, height } = canvas;

                let color = "red";
                if (zone.type === "warning") color = "yellow";
                else if (zone.type === "safe") color = "limegreen";

                if (mode === "edit") {
                    ctx.globalAlpha = zone.id === editingZoneId ? 1.0 : 0.4;
                    ctx.lineWidth = zone.id === editingZoneId ? 4 : 2;
                } else {
                    ctx.globalAlpha = 1.0;
                    ctx.lineWidth = 2;
                }

                ctx.beginPath();
                ctx.moveTo(zone.points[0][0] * width, zone.points[0][1] * height);
                for (let i = 1; i < zone.points.length; i++) {
                    ctx.lineTo(zone.points[i][0] * width, zone.points[i][1] * height);
                }
                if (zone.points.length > 2) ctx.closePath();
                ctx.strokeStyle = color;
                ctx.stroke();

                zone.points.forEach(([relX, relY]) => {
                    ctx.beginPath();
                    ctx.arc(relX * width, relY * height, 4, 0, Math.PI * 2);
                    ctx.fillStyle = color;
                    ctx.fill();
                });

                if (isZoneMenuOpen) {
                    const absPoints = zone.points.map(([rx, ry]) => [rx * width, ry * height]);
                    const center = getCenterOfPolygon(absPoints);
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

            if (currentDrawingPoints && currentDrawingPoints.length > 0) {
                ctx.beginPath();
                ctx.moveTo(currentDrawingPoints[0][0], currentDrawingPoints[0][1]);
                for (let i = 1; i < currentDrawingPoints.length; i++) {
                    ctx.lineTo(currentDrawingPoints[i][0], currentDrawingPoints[i][1]);
                }
                
                ctx.strokeStyle = "red";
                ctx.lineWidth = 2;
                ctx.stroke();
                currentDrawingPoints.forEach(([x, y]) => {
                    ctx.beginPath();
                    ctx.arc(x, y, 5, 0, Math.PI * 2);
                    ctx.fillStyle = "red";
                    ctx.fill();
                });
            }
        }
    }, [zones, isActive, isZoneMenuOpen, currentDrawingPoints, mode, editingZoneId, canvasSize]);

    const handleClicks = (e, type) => {
        e.stopPropagation();

        if (mode === "draw") {
            if (type === 'single') {
                const rect = canvasRef.current.getBoundingClientRect();
                onPointAdd([e.clientX - rect.left, e.clientY - rect.top]);
            }
            return;
        }

        if (type === 'single') {
            if (clickTimer.current) {
                clearTimeout(clickTimer.current);
            }
            clickTimer.current = setTimeout(() => {
                onSelect(camera.id);
                clickTimer.current = null;
            }, 200);
        } else if (type === 'double') {
            if (clickTimer.current) {
                clearTimeout(clickTimer.current);
                clickTimer.current = null;
            }
            onDoubleClick(camera.id);
        }
    };

    return (
        <div 
            className={`camera-tile ${isActive ? 'active' : ''} ${isFocused ? 'focused' : ''}`}
            onClick={(e) => handleClicks(e, 'single')}
            onDoubleClick={(e) => handleClicks(e, 'double')}
        >
            <div className="video-inner">
                <video ref={videoRef} src={camera.src} autoPlay loop muted playsInline />
                <canvas ref={canvasRef} />
            </div>
            <div className="camera-label">{camera.name || `Камера ${camera.id}`}</div>
        </div>
    );
}