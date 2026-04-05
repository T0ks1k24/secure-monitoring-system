import { useState } from "react";
import { useGetCamerasQuery } from "../../../services/camerasApi";
import SlotCameraPickerModal from "./SlotCameraPickerModal";

const getGridLayout = (count) => {
    if (count === 4)  return { cols: 2, rows: 2 };
    if (count === 6)  return { cols: 3, rows: 2 };
    if (count === 9)  return { cols: 3, rows: 3 };
    if (count === 12) return { cols: 4, rows: 3 };
    if (count === 16) return { cols: 4, rows: 4 };
    return { cols: 3, rows: 3 };
};

const loadSlotConfig = (count) => {
    try {
        const saved = localStorage.getItem("slot_config");
        if (!saved) return Array(count).fill(null);
        const parsed = JSON.parse(saved);
        const result = Array(count).fill(null);
        parsed.forEach((id, i) => { if (i < count) result[i] = id; });
        return result;
    } catch { return Array(count).fill(null); }
};

const saveSlotConfig = (config) => {
    localStorage.setItem("slot_config", JSON.stringify(config));
};

export default function DisplaySettings() {
    const { data: cameras = [] } = useGetCamerasQuery();

    const [slotCount, setSlotCount] = useState(() =>
        parseInt(localStorage.getItem("grid_slot_count") || "9")
    );
    const [slots, setSlots] = useState(() => loadSlotConfig(
        parseInt(localStorage.getItem("grid_slot_count") || "9")
    ));
    const [pickerSlotIndex, setPickerSlotIndex] = useState(null);
    
    const [dragFromIndex, setDragFromIndex] = useState(null);

    const handleSlotCountChange = (count) => {
        setSlotCount(count);
        localStorage.setItem("grid_slot_count", String(count));
        const newSlots = Array(count).fill(null);
        slots.forEach((id, i) => { if (i < count) newSlots[i] = id; });
        setSlots(newSlots);
        saveSlotConfig(newSlots);
    };

    const handleSelectCamera = (cameraId) => {
        if (pickerSlotIndex === null) return;
        const newSlots = [...slots];
        newSlots[pickerSlotIndex] = cameraId;
        setSlots(newSlots);
        saveSlotConfig(newSlots);
        setPickerSlotIndex(null);
    };

    const handleRemoveCamera = (slotIndex) => {
        const newSlots = [...slots];
        newSlots[slotIndex] = null;
        setSlots(newSlots);
        saveSlotConfig(newSlots);
    };

    const occupiedCameraIds = slots.filter(Boolean);
    const { cols, rows } = getGridLayout(slotCount);

    const getCameraById = (id) => cameras.find(c => String(c.id) === String(id));

    return (
        <div className="tab-content">
            <h2>Відображення</h2>

            <div className="setting-row">
                <label>Кількість слотів на головному екрані</label>
                <div className="slot-options">
                    {[4, 6, 9, 12, 16].map(n => (
                        <button
                            key={n}
                            className={`slot-btn ${slotCount === n ? "active" : ""}`}
                            onClick={() => handleSlotCountChange(n)}
                        >
                            {n}
                        </button>
                    ))}
                </div>
            </div>

            <div className="setting-row">
                <label>Попередній перегляд сітки</label>
                <div
                    className="grid-preview"
                    style={{
                        display: "grid",
                        gridTemplateColumns: `repeat(${cols}, 1fr)`,
                        gridTemplateRows: `repeat(${rows}, 1fr)`,
                        gap: "3px",
                        width: "480px",
                        height: "270px",
                        background: "#020617",
                        padding: "3px",
                        borderRadius: "8px",
                        border: "1px solid #1e293b",
                    }}
                >
                    {slots.map((cameraId, i) => {
                        const cam = cameraId ? getCameraById(cameraId) : null;
                        return (
                            <div
                                key={i}
                                className="preview-slot"
                                draggable={!!cam}
                                onDragStart={() => setDragFromIndex(i)}
                                onDragOver={(e) => e.preventDefault()}
                                onDrop={() => {
                                    if (dragFromIndex === null || dragFromIndex === i) return;
                                    const newSlots = [...slots];
                                    const temp = newSlots[dragFromIndex];
                                    newSlots[dragFromIndex] = newSlots[i];
                                    newSlots[i] = temp;
                                    setSlots(newSlots);
                                    saveSlotConfig(newSlots);
                                    setDragFromIndex(null);
                                }}
                                onDragEnd={() => setDragFromIndex(null)}
                                style={{
                                    background: dragFromIndex === i ? "#1e3a5f" : "#0f172a",
                                    border: "1px solid #1e293b",
                                    borderRadius: "4px",
                                    display: "flex",
                                    alignItems: "center",
                                    justifyContent: "center",
                                    position: "relative",
                                    overflow: "hidden",
                                    minHeight: 0,
                                }}
                            >
                                {cam ? (
                                    <>
                                        <span style={{ color: "#cbd5e1", fontSize: "11px", textAlign: "center", padding: "4px" }}>
                                            {cam.name || `Камера ${cam.id}`}
                                        </span>
                                        <button
                                            onClick={() => handleRemoveCamera(i)}
                                            style={{
                                                position: "absolute",
                                                top: "2px",
                                                right: "2px",
                                                background: "rgba(127,29,29,0.8)",
                                                border: "none",
                                                color: "white",
                                                width: "18px",
                                                height: "18px",
                                                borderRadius: "3px",
                                                cursor: "pointer",
                                                fontSize: "10px",
                                                display: "flex",
                                                alignItems: "center",
                                                justifyContent: "center",
                                                lineHeight: 1,
                                            }}
                                        >
                                            ✕
                                        </button>
                                    </>
                                ) : (
                                    <button
                                        onClick={() => setPickerSlotIndex(i)}
                                        style={{
                                            background: "none",
                                            border: "1px dashed #334155",
                                            color: "#475569",
                                            width: "28px",
                                            height: "28px",
                                            borderRadius: "50%",
                                            cursor: "pointer",
                                            fontSize: "18px",
                                            display: "flex",
                                            alignItems: "center",
                                            justifyContent: "center",
                                            transition: "all 0.2s",
                                        }}
                                        onMouseEnter={e => { e.currentTarget.style.borderColor = "#2563eb"; e.currentTarget.style.color = "#2563eb"; }}
                                        onMouseLeave={e => { e.currentTarget.style.borderColor = "#334155"; e.currentTarget.style.color = "#475569"; }}
                                    >
                                        <svg width="12" height="12" viewBox="0 0 12 12" fill="currentColor">
                                            <rect x="5" y="0" width="2" height="12" rx="1" />
                                            <rect x="0" y="5" width="12" height="2" rx="1" />
                                        </svg>
                                    </button>
                                )}
                            </div>
                        );
                    })}
                </div>
            </div>

            {pickerSlotIndex !== null && (
                <SlotCameraPickerModal
                    allCameras={cameras}
                    occupiedCameraIds={occupiedCameraIds}
                    onSelect={handleSelectCamera}
                    onClose={() => setPickerSlotIndex(null)}
                />
            )}
        </div>
    );
}