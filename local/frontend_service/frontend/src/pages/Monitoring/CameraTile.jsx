import { useRef, useEffect, useLayoutEffect, useState } from "react";
import { useGetZonesQuery } from "../../services/zonesApi";

const getCenterOfPolygon = (points) => {
    if (!points || points.length === 0) return { x: 0, y: 0 };
    const x = points.reduce((sum, p) => sum + p[0], 0) / points.length;
    const y = points.reduce((sum, p) => sum + p[1], 0) / points.length;
    return { x, y };
};

function isZoneRelaxed(zone, now) {
    if (!zone.time_windows || zone.time_windows.length === 0) return false;
    const currentMinutes = now.getHours() * 60 + now.getMinutes();
    return zone.time_windows.some(tw => {
        if (!tw.start || !tw.end) return false;
        const [sh, sm] = tw.start.split(":").map(Number);
        const [eh, em] = tw.end.split(":").map(Number);
        return currentMinutes >= sh * 60 + sm && currentMinutes <= eh * 60 + em;
    });
}

const ZONE_COLORS = {
    restricted: "#ff0000", danger:        "#ff0000",
    perimeter:  "#ffb700", warning:       "#ffb700",
    safe_zone:  "#00ff5e", safe:          "#00ff5e",
    pedestrian: "#0073ff",
    counting_line: "#b57200",
    entrance:   "#8000ff", parking:       "#7f00ff",
};

export default function CameraTile({
    camera, isFocused, isZoneMenuOpen, currentDrawingPoints, onPointAdd,
    mode, editingZoneId, isPanelOpen, isRedrawing = false
}) {
    const mediaRef = useRef(null);
    const canvasRef = useRef(null);
    const [canvasSize, setCanvasSize] = useState({ width: 0, height: 0 });
    const [currentTime, setCurrentTime] = useState(new Date());

    const { data: zones = [] } = useGetZonesQuery(camera.zoneCameraId || camera.id);

    useEffect(() => {
        const timer = setInterval(() => setCurrentTime(new Date()), 1000);
        return () => clearInterval(timer);
    }, []);

    useLayoutEffect(() => {
        const media = mediaRef.current;
        const canvas = canvasRef.current;
        if (!media || !canvas) return;

        const updateSize = () => {
            const { width, height } = media.getBoundingClientRect();
            canvas.width = width;
            canvas.height = height;
            setCanvasSize({ width, height });
        };
        const resizeObserver = new ResizeObserver(() => updateSize());
        resizeObserver.observe(media);
        updateSize();
        return () => resizeObserver.disconnect();
    }, [isFocused, isPanelOpen]);

    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;
        const ctx = canvas.getContext("2d");
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        zones.forEach(zone => {
            if (!zone.points || zone.points.length < 2) return;
            const { width, height } = canvas;
            const color = ZONE_COLORS[zone.zone_type] || "#ff0000";
            const relaxed = isZoneRelaxed(zone, currentTime);

            if (mode === "edit") {
                if (isRedrawing) {
                    ctx.globalAlpha = 0.25;
                    ctx.lineWidth = 1;
                } else {
                    ctx.globalAlpha = zone.id === editingZoneId ? 1.0 : 0.4;
                    ctx.lineWidth   = zone.id === editingZoneId ? 4   : 2;
                }
            } else {
                ctx.globalAlpha = relaxed ? 0.35 : 1.0;
                ctx.lineWidth   = relaxed ? 1    : 2;
            }

            ctx.setLineDash(relaxed && mode !== "edit" ? [6, 4] : []);

            ctx.beginPath();
            ctx.moveTo(zone.points[0][0] * width, zone.points[0][1] * height);
            for (let i = 1; i < zone.points.length; i++) {
                ctx.lineTo(zone.points[i][0] * width, zone.points[i][1] * height);
            }
            if (zone.points.length > 2) ctx.closePath();
            ctx.strokeStyle = color;
            ctx.stroke();
            ctx.setLineDash([]);

            zone.points.forEach(([relX, relY]) => {
                ctx.beginPath();
                ctx.arc(relX * width, relY * height, 4, 0, Math.PI * 2);
                ctx.fillStyle = color;
                ctx.fill();
            });

            if (isZoneMenuOpen && !isRedrawing) {
                const absPoints = zone.points.map(([rx, ry]) => [rx * width, ry * height]);
                const center = getCenterOfPolygon(absPoints);
                ctx.globalAlpha = mode === "edit" && zone.id !== editingZoneId ? 0.4 : 1.0;
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
        ctx.setLineDash([]);

        if (currentDrawingPoints && currentDrawingPoints.length > 0) {
            ctx.beginPath();
            ctx.moveTo(currentDrawingPoints[0][0], currentDrawingPoints[0][1]);
            for (let i = 1; i < currentDrawingPoints.length; i++) {
                ctx.lineTo(currentDrawingPoints[i][0], currentDrawingPoints[i][1]);
            }
            ctx.strokeStyle = "#ff0000";
            ctx.lineWidth = 2;
            ctx.stroke();

            currentDrawingPoints.forEach(([x, y]) => {
                ctx.beginPath();
                ctx.arc(x, y, 5, 0, Math.PI * 2);
                ctx.fillStyle = "#ff0000";
                ctx.fill();
            });
        }
    }, [zones, isZoneMenuOpen, currentDrawingPoints, mode, editingZoneId, canvasSize, currentTime, isRedrawing]);

    const handleClick = (e) => {
        if (mode !== "draw" && !(mode === "edit" && isRedrawing)) return;
        const rect = canvasRef.current.getBoundingClientRect();
        onPointAdd([e.clientX - rect.left, e.clientY - rect.top]);
    };

    return (
        <div className="camera-tile">
            <div className="video-inner">
                {camera.webrtcUrl ? (
                    <iframe
                        ref={mediaRef}
                        src={camera.webrtcUrl}
                        allow="autoplay; fullscreen"
                        title={`camera-stream-${camera.id}`}
                        style={{ pointerEvents: "none" }}
                    />
                ) : (
                    <video
                        ref={mediaRef}
                        src={camera.src}
                        autoPlay loop muted playsInline
                        controls={false}
                        disablePictureInPicture
                        controlsList="nodownload noplaybackrate noremoteplayback nofullscreen"
                    />
                )}
                <canvas
                    ref={canvasRef}
                    onClick={handleClick}
                    style={{
                        pointerEvents: (mode === "draw" || (mode === "edit" && isRedrawing))
                            ? "auto"
                            : "none"
                    }}
                />
            </div>
        </div>
    );
}