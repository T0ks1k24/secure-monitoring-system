import { useRef, useEffect, useLayoutEffect } from "react";
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
    const { data: zones = [] } = useGetZonesQuery(camera.id);

    useLayoutEffect(() => {
        const video = videoRef.current;
        const canvas = canvasRef.current;
        if (!video || !canvas) return;

        const updateSize = () => {
            const { width, height } = video.getBoundingClientRect();
            canvas.width = width;
            canvas.height = height;
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
                if (mode === "edit") {
                    ctx.globalAlpha = zone.id === editingZoneId ? 1.0 : 0.4;
                    ctx.lineWidth = zone.id === editingZoneId ? 4 : 2;
                } else {
                    ctx.globalAlpha = 1.0;
                    ctx.lineWidth = 2;
                }

                let color;
                switch (zone.zone_type) {
                    case "danger": color = "red"; break;
                    case "warning": color = "yellow"; break;
                    case "safe": color = "limegreen"; break;
                    default: color = "red";
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
    }, [zones, isActive, isZoneMenuOpen, currentDrawingPoints, mode, editingZoneId]);

    return (
        <div 
            className={`camera-tile ${isActive ? 'active' : ''} ${isFocused ? 'focused' : ''}`}
            onClick={() => onSelect(camera.id)}
            onDoubleClick={() => onDoubleClick(camera.id)}
        >
            <div className="video-inner">
                <video ref={videoRef} src={camera.src} autoPlay loop muted playsInline />
                <canvas
                    ref={canvasRef}
                    onClick={(e) => {
                        e.stopPropagation();
                        if (mode === "draw") {
                            const rect = canvasRef.current.getBoundingClientRect();
                            onPointAdd([e.clientX - rect.left, e.clientY - rect.top]);
                        } else {
                            onSelect(camera.id);
                        }
                    }}
                    onDoubleClick={(e) => {
                        e.stopPropagation();
                        onDoubleClick(camera.id);
                    }} 
                />
            </div>
            <div className="camera-label">{camera.name || `Камера ${camera.id}`}</div>
        </div>
    );
}