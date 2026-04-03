import React, { useState, useEffect } from "react";

export default function CameraSelectionModal({ allCameras, selectedCameras, onClose, onSave, activeCameraIdFromUrl }) {
    
    const [tempIds, setTempIds] = useState(selectedCameras.map(c => c.id));
    const [errorId, setErrorId] = useState(null);

    useEffect(() => {
        if (errorId) {
            const timer = setTimeout(() => setErrorId(null), 2000);
            return () => clearTimeout(timer);
        }
    }, [errorId]);

    const toggleCamera = (id) => {
        if (id === String(activeCameraIdFromUrl)) return;

        if (tempIds.includes(id)) {
            setTempIds(prev => prev.filter(i => i !== id));
            setErrorId(null);
        } else {
            if (tempIds.length >= 4) {
                setErrorId(id);
                return;
            }
            setTempIds(prev => [...prev, id]);
            setErrorId(null);
        }
    };

    const handleSave = () => {
        const newSelection = allCameras.filter(c => tempIds.includes(c.id));
        onSave(newSelection);
    };

    return (
        <div className="modal-overlay">
            <div className="modal-box" style={{ maxWidth: "450px", width: "90%" }}>
                <h3 style={{ color: "white", marginBottom: "20px" }}>Додати камери до мережі</h3>
                
                <div className="camera-selection-list" style={{ maxHeight: "350px", overflowY: "auto", marginBottom: "20px" }}>
                    {allCameras.map(cam => {
                        const isMainCamera = cam.id === String(activeCameraIdFromUrl);

                        return (
                            <div 
                                key={cam.id} 
                                className={`zone-item ${tempIds.includes(cam.id) ? 'selected' : ''}`}
                                style={{ 
                                    cursor: isMainCamera ? "not-allowed" : "pointer",
                                    display: "flex", 
                                    alignItems: "center", 
                                    gap: "12px", 
                                    padding: "12px",
                                    opacity: isMainCamera ? 0.7 : 1
                                }}
                                onClick={() => toggleCamera(cam.id)}
                            >
                                <input 
                                    type="checkbox" 
                                    checked={tempIds.includes(cam.id)} 
                                    readOnly 
                                    disabled={isMainCamera}
                                    style={{ width: "18px", height: "18px", pointerEvents: "none" }}
                                />
                                <div style={{ display: "flex", flexDirection: "column", flex: 1 }}>
                                    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                                        <span style={{ color: "white", fontWeight: "600" }}>{cam.name}</span>
                                        {isMainCamera && (
                                            <span style={{ color: "#2563eb", fontSize: "10px", background: "rgba(37, 99, 235, 0.2)", padding: "2px 6px", borderRadius: "4px" }}>
                                                ПОТОЧНА
                                            </span>
                                        )}
                                    </div>
                                    
                                    {errorId === cam.id ? (
                                        <span style={{ color: "#ef4444", fontSize: "11px", fontWeight: "bold" }}>
                                            Максимум 4 камери!
                                        </span>
                                    ) : (
                                        <span style={{ color: "#64748b", fontSize: "11px" }}>
                                            {isMainCamera ? "Цю камеру не можна вимкнути тут" : `ID: ${cam.id}`}
                                        </span>
                                    )}
                                </div>
                            </div>
                        );
                    })}
                </div>

                <div style={{ display: "flex", gap: "10px" }}>
                    <button className="start-btn" onClick={handleSave} style={{ flex: 2, margin: 0 }}>Оновити сітку</button>
                    <button onClick={onClose} style={{ flex: 1, padding: "10px", borderRadius: "6px", background: "#475569", color: "white", border: "none", cursor: "pointer" }}>Скасувати</button>
                </div>
            </div>
        </div>
    );
}