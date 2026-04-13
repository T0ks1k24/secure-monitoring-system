import React, { useState, useEffect } from 'react';
import './AddCameraModal.scss';

const InfoIcon = ({ text }) => (
    <span className="info-tooltip" data-tooltip={text}>?</span>
);

const defaultData = {
    rtsp: '',
    name: '',
    enabled: true,
    fps: 5.0,
    resize_width: 1280,
    jpeg_quality: 80,
    reconnect_delay: 5,
    motion: {
        enabled: true,
        min_contour_area: 4000,
        min_total_area: 6000,
        min_solidity: 0.4,
        min_consecutive_frames: 2,
        cooldown_seconds: 10.0,
        blur_size: 21,
        diff_threshold: 25,
        dilate_iterations: 2,
        background_update_alpha: 0.05
    }
};

export default function AddCameraModal({ isOpen, onClose, onSave, initialValues }) {
    const [formData, setFormData] = useState(defaultData);
    const [showAdvanced, setShowAdvanced] = useState(false);

    useEffect(() => {
        if (isOpen) {
            setFormData(initialValues || defaultData);
            setShowAdvanced(false);
        }
    }, [isOpen, initialValues]);

    if (!isOpen) return null;

    const isEditMode = !!initialValues;
    const set = (field, value) => setFormData(prev => ({ ...prev, [field]: value }));
    const setMotion = (field, value) => setFormData(prev => ({ ...prev, motion: { ...prev.motion, [field]: value } }));
    const num = (val, float = false) => val === '' ? val : (float ? parseFloat(val) : parseInt(val, 10));

    const handleSubmit = (e) => {
        e.preventDefault();
        onSave({
            ...formData,
            fps: formData.fps === '' ? 5.0 : formData.fps,
            resize_width: formData.resize_width === '' ? 1280 : formData.resize_width,
            jpeg_quality: formData.jpeg_quality === '' ? 80 : formData.jpeg_quality,
        });
    };

    return (
        <div className="modal-overlay">
            <div className={`modal-content ${showAdvanced ? "with-advanced" : ""}`}>

                <div className="modal-main">
                    <header>
                        <h3>{isEditMode ? `Edit camera ${formData.id ?? ""}` : 'Add new camera'}</h3>
                        <button className="close-x" onClick={onClose}>✕</button>
                    </header>

                    <form onSubmit={handleSubmit}>
                        <div className="form-grid">
                            <div className="input-group">
                                <label>Camera name</label>
                                <input
                                    placeholder="e.g. Main entrance"
                                    value={formData.name || ''}
                                    onChange={e => set('name', e.target.value)}
                                />
                            </div>

                            <div className="input-group full">
                                <label>RTSP stream <InfoIcon text="RTSP stream URL for the camera source." /></label>
                                <input
                                    required
                                    placeholder="rtsp://mediamtx:8554/camera1"
                                    value={formData.rtsp}
                                    onChange={e => set('rtsp', e.target.value)}
                                />
                                <small>For Docker Compose: <code>rtsp://mediamtx:8554/camera1</code></small>
                            </div>

                            <div className="input-group">
                                <label>FPS <InfoIcon text="Frames per second. Recommended: 1.0–5.0 for detection." /></label>
                                <input
                                    type="number" step="0.5" min="0.1" max="30"
                                    value={formData.fps}
                                    onChange={e => set('fps', num(e.target.value, true))}
                                />
                            </div>

                            <div className="input-group">
                                <label>Resize width (px) <InfoIcon text="Frame width in pixels. Recommended: 1280 for quality/speed balance." /></label>
                                <input
                                    type="number" min="0"
                                    value={formData.resize_width}
                                    onChange={e => set('resize_width', num(e.target.value))}
                                />
                            </div>

                            <div className="input-group">
                                <label>JPEG quality <InfoIcon text="Frame compression quality (1–100). Higher = better quality, more bandwidth." /></label>
                                <input
                                    type="number" min="1" max="100"
                                    value={formData.jpeg_quality}
                                    onChange={e => set('jpeg_quality', num(e.target.value))}
                                />
                            </div>
                        </div>

                        <div className="modal-footer">
                            <div className="footer-actions">
                                <button type="button" className="cancel-btn" onClick={onClose}>Cancel</button>
                                <button type="submit" className="save-btn">Save</button>
                            </div>
                            <button
                                type="button"
                                className={`advanced-btn ${showAdvanced ? "active" : ""}`}
                                onClick={() => setShowAdvanced(p => !p)}
                            >
                                Advanced {showAdvanced ? "◀" : "▶"}
                            </button>
                        </div>
                    </form>
                </div>

                {showAdvanced && (
                    <div className="modal-advanced">
                        <h4>Advanced settings</h4>

                        <div className="adv-section">
                            <span className="adv-section-title">Connection</span>
                            <div className="adv-row">
                                <div className="input-group">
                                    <label>Reconnect delay (sec) <InfoIcon text="Seconds to wait before reconnecting after connection loss." /></label>
                                    <input
                                        type="number" min="1"
                                        value={formData.reconnect_delay}
                                        onChange={e => set('reconnect_delay', num(e.target.value))}
                                    />
                                </div>
                            </div>
                        </div>

                        <div className="adv-section">
                            <span className="adv-section-title">Motion detection</span>

                            <div className="adv-toggle">
                                <span>Enabled</span>
                                <button
                                    type="button"
                                    className={`toggle-btn ${formData.motion.enabled ? "on" : "off"}`}
                                    onClick={() => setMotion("enabled", !formData.motion.enabled)}
                                >
                                    {formData.motion.enabled ? "ON" : "OFF"}
                                </button>
                            </div>

                            <div className="adv-row">
                                <div className="input-group">
                                    <label>Min contour area <InfoIcon text="Minimum area of a single moving contour (px²)." /></label>
                                    <input type="number" value={formData.motion.min_contour_area}
                                        onChange={e => setMotion("min_contour_area", num(e.target.value))} />
                                </div>
                                <div className="input-group">
                                    <label>Min total area <InfoIcon text="Minimum total area of all contours combined to trigger detection (px²)." /></label>
                                    <input type="number" value={formData.motion.min_total_area}
                                        onChange={e => setMotion("min_total_area", num(e.target.value))} />
                                </div>
                            </div>

                            <div className="adv-row">
                                <div className="input-group">
                                    <label>Min solidity <InfoIcon text="Minimum shape solidity [0.1–1]. Higher = more compact shapes required." /></label>
                                    <input type="number" step="0.1" min="0.1" max="1" value={formData.motion.min_solidity}
                                        onChange={e => setMotion("min_solidity", num(e.target.value, true))} />
                                </div>
                                <div className="input-group">
                                    <label>Consecutive frames <InfoIcon text="Frames with motion required before triggering an event [1–10]." /></label>
                                    <input type="number" min="1" max="10" value={formData.motion.min_consecutive_frames}
                                        onChange={e => setMotion("min_consecutive_frames", num(e.target.value))} />
                                </div>
                            </div>

                            <div className="adv-row">
                                <div className="input-group">
                                    <label>Cooldown (sec) <InfoIcon text="Minimum seconds between motion events from this camera." /></label>
                                    <input type="number" step="0.5" value={formData.motion.cooldown_seconds}
                                        onChange={e => setMotion("cooldown_seconds", num(e.target.value, true))} />
                                </div>
                                <div className="input-group">
                                    <label>Blur size <InfoIcon text="Gaussian blur kernel size for noise reduction. Must be odd, ≥3." /></label>
                                    <input type="number" min="3" step="2" value={formData.motion.blur_size}
                                        onChange={e => setMotion("blur_size", num(e.target.value))} />
                                </div>
                            </div>

                            <div className="adv-row">
                                <div className="input-group">
                                    <label>Diff threshold <InfoIcon text="Pixel intensity difference threshold [1–255]. Lower = more sensitive." /></label>
                                    <input type="number" min="1" max="255" value={formData.motion.diff_threshold}
                                        onChange={e => setMotion("diff_threshold", num(e.target.value))} />
                                </div>
                                <div className="input-group">
                                    <label>Dilate iterations <InfoIcon text="Dilation passes to fill holes in detected contours [1–5]." /></label>
                                    <input type="number" min="1" max="5" value={formData.motion.dilate_iterations}
                                        onChange={e => setMotion("dilate_iterations", num(e.target.value))} />
                                </div>
                            </div>

                            <div className="adv-row">
                                <div className="input-group">
                                    <label>BG update alpha <InfoIcon text="Background model learning rate [0–1]. Lower = slower adaptation." /></label>
                                    <input type="number" step="0.01" min="0" max="1" value={formData.motion.background_update_alpha}
                                        onChange={e => setMotion("background_update_alpha", num(e.target.value, true))} />
                                </div>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}