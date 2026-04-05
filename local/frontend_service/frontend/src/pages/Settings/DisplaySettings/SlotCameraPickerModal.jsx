export default function SlotCameraPickerModal({ allCameras, occupiedCameraIds, onSelect, onClose }) {
    return (
        <div className="modal-overlay">
            <div className="modal-box" style={{ maxWidth: "400px", width: "90%" }}>
                <h3 style={{ color: "white", marginBottom: "20px" }}>Виберіть камеру</h3>

                <div style={{ maxHeight: "350px", overflowY: "auto", marginBottom: "20px", display: "flex", flexDirection: "column", gap: "8px" }}>
                    {allCameras.map(cam => {
                        const isOccupied = occupiedCameraIds.includes(String(cam.id));
                        return (
                            <div
                                key={cam.id}
                                onClick={() => !isOccupied && onSelect(String(cam.id))}
                                style={{
                                    padding: "12px",
                                    borderRadius: "8px",
                                    background: "#0f172a",
                                    border: "1px solid #334155",
                                    cursor: isOccupied ? "not-allowed" : "pointer",
                                    opacity: isOccupied ? 0.4 : 1,
                                    display: "flex",
                                    flexDirection: "column",
                                    gap: "4px",
                                    transition: "border-color 0.2s",
                                }}
                                onMouseEnter={e => { if (!isOccupied) e.currentTarget.style.borderColor = "#2563eb"; }}
                                onMouseLeave={e => { e.currentTarget.style.borderColor = "#334155"; }}
                            >
                                <span style={{ color: "white", fontWeight: "600" }}>{cam.name || `Камера ${cam.id}`}</span>
                                <span style={{ color: "#64748b", fontSize: "11px" }}>
                                    {isOccupied ? "Вже додана" : `ID: ${cam.id}`}
                                </span>
                            </div>
                        );
                    })}
                </div>

                <button
                    onClick={onClose}
                    style={{ width: "100%", padding: "10px", borderRadius: "6px", background: "#475569", color: "white", border: "none", cursor: "pointer" }}
                >
                    Скасувати
                </button>
            </div>
        </div>
    );
}