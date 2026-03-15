import React, { useState, useEffect } from 'react';
import './AddCameraModal.scss';

export default function AddCameraModal({ isOpen, onClose, onSave, initialValues }) {
    const defaultData = {
        id: '',
        rtsp: '',
        name: '',
        enabled: true,
        fps: 5.0,
        resize_width: 1280,
        jpeg_quality: 80,
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

    const [formData, setFormData] = useState(defaultData);

    useEffect(() => {
        if (isOpen) {
            if (initialValues) {
                setFormData(initialValues);
            } else {
                setFormData(defaultData);
            }
        }
    }, [isOpen, initialValues]);

    if (!isOpen) return null;

    const isEditMode = !!initialValues;

    const handleNumberChange = (field, value, isFloat = false) => {
        if (value === '') {
            setFormData(prev => ({ ...prev, [field]: '' }));
            return;
        }
        const parsedValue = isFloat ? parseFloat(value) : parseInt(value, 10);
        setFormData(prev => ({ ...prev, [field]: parsedValue }));
    };

    const handleSubmit = (e) => {
        e.preventDefault();

        const finalData = {
            ...formData,
            fps: formData.fps === '' ? 5.0 : formData.fps,
            resize_width: formData.resize_width === '' ? 1280 : formData.resize_width,
            jpeg_quality: formData.jpeg_quality === '' ? 80 : formData.jpeg_quality,
        };

        onSave(finalData);
        setFormData(defaultData);
    };

    return (
        <div className="modal-overlay">
            <div className="modal-content">
                <header>
                    <h3>{isEditMode ? `Редагувати камеру ${formData.id}` : 'Додати нову камеру'}</h3>
                    <button className="close-x" onClick={onClose}>✕</button>
                </header>

                <form onSubmit={handleSubmit}>
                    <div className="form-grid">
                        <div className="input-group">
                            <label>Унікальний ID</label>
                            <input
                                required
                                placeholder="напр: entrance"
                                value={formData.id}
                                disabled={isEditMode} 
                                style={isEditMode ? { opacity: 0.6, cursor: 'not-allowed' } : {}}
                                onChange={e => setFormData({ ...formData, id: e.target.value })}
                            />
                        </div>

                        <div className="input-group">
                            <label>Назва камери</label>
                            <input
                                placeholder="напр: Головний вхід"
                                value={formData.name}
                                onChange={e => setFormData({ ...formData, name: e.target.value })}
                            />
                        </div>

                        <div className="input-group full">
                            <label>RTSP Потік</label>
                            <input
                                required
                                placeholder="rtsp://127.0.0.1:8554/camera1"
                                value={formData.rtsp}
                                onChange={e => setFormData({ ...formData, rtsp: e.target.value })}
                            />
                        </div>

                        <div className="input-group">
                            <label>FPS</label>
                            <input
                                type="number"
                                step="0.1"
                                value={formData.fps}
                                onChange={e => handleNumberChange('fps', e.target.value, true)}
                            />
                        </div>

                        <div className="input-group">
                            <label>Resize Width (px)</label>
                            <input
                                type="number"
                                value={formData.resize_width}
                                onChange={e => handleNumberChange('resize_width', e.target.value)}
                            />
                        </div>

                        <div className="input-group">
                            <label>Якість JPEG (1-100)</label>
                            <input
                                type="number"
                                min="1"
                                max="100"
                                value={formData.jpeg_quality}
                                onChange={e => handleNumberChange('jpeg_quality', e.target.value)}
                            />
                        </div>
                    </div>

                    <div className="modal-footer">
                        <button type="button" className="cancel-btn" onClick={onClose}>Скасувати</button>
                        <button type="submit" className="save-btn">Зберегти</button>
                    </div>
                </form>
            </div>
        </div>
    );
}