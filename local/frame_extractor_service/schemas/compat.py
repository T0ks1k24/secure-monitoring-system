from __future__ import annotations

from typing import Any

from pydantic import BaseModel

LEGACY_MOTION_FIELD_MAP = {
    "motion_min_contour_area": "min_contour_area",
    "motion_threshold": "diff_threshold",
    "motion_blur_size": "blur_size",
    "motion_frames_to_average": "min_consecutive_frames",
    "motion_min_duration": "cooldown_seconds",
}

LEGACY_GLOBAL_FIELD_MAP = {
    "fps": "default_fps",
    "resize_width": "default_resize_width",
    "jpeg_quality": "default_jpeg_quality",
    "reconnect_delay": "default_reconnect_delay",
}


def _as_dict(payload: Any) -> dict[str, Any] | None:
    if isinstance(payload, BaseModel):
        return payload.model_dump(exclude_none=True)
    if isinstance(payload, dict):
        return dict(payload)
    return None


def fold_legacy_motion_fields(data: Any) -> Any:
    if not isinstance(data, dict):
        return data

    normalized = dict(data)
    motion_updates = {
        nested_key: normalized.pop(flat_key)
        for flat_key, nested_key in LEGACY_MOTION_FIELD_MAP.items()
        if flat_key in normalized and normalized[flat_key] is not None
    }
    if not motion_updates:
        return normalized

    current_motion = _as_dict(normalized.get("motion")) or {}
    normalized["motion"] = {**motion_updates, **current_motion}
    return normalized


def fold_legacy_global_fields(data: Any) -> Any:
    if not isinstance(data, dict):
        return data

    normalized = dict(data)
    for legacy_key, actual_key in LEGACY_GLOBAL_FIELD_MAP.items():
        if normalized.get(actual_key) is None and normalized.get(legacy_key) is not None:
            normalized[actual_key] = normalized[legacy_key]
    return normalized
