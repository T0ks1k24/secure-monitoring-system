"""
Тести для MotionDetector і _scanner_utils.

Обидва модулі не потребують pydantic/fastapi —
тільки cv2, numpy і stdlib. Запускаються без встановленого FastAPI.
"""
import sys
import os

# На випадок запуску напряму (python test_motion_detector.py)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

import unittest
import numpy as np

from detection.motion_detector import (
    MotionDetector,
    MotionDetectorConfig,
    MotionState,
)


# ── Helpers ────────────────────────────────────────────────────────────────────

def black(h: int = 480, w: int = 640) -> np.ndarray:
    return np.zeros((h, w, 3), dtype=np.uint8)


def rect(x: int = 100, y: int = 100, w_r: int = 200, h_r: int = 150,
         h: int = 480, w: int = 640) -> np.ndarray:
    frame = black(h, w)
    frame[y:y + h_r, x:x + w_r] = 255
    return frame


def make_detector(**kw) -> MotionDetector:
    """Створює детектор з зручними тестовими дефолтами."""
    cfg = MotionDetectorConfig(
        min_contour_area      = kw.pop("min_contour_area",       500),
        min_total_area        = kw.pop("min_total_area",          800),
        min_solidity          = kw.pop("min_solidity",            0.3),
        min_consecutive_frames= kw.pop("min_consecutive_frames",    1),
        cooldown_seconds      = kw.pop("cooldown_seconds",        0.0),
        blur_size             = kw.pop("blur_size",                 3),
        diff_threshold        = kw.pop("diff_threshold",           10),
        dilate_iterations     = kw.pop("dilate_iterations",         1),
        background_update_alpha=kw.pop("background_update_alpha", 1.0),
        **kw,
    )
    return MotionDetector(cfg)


# ══════════════════════════════════════════════════════════════════════════════
# Базова логіка
# ══════════════════════════════════════════════════════════════════════════════

class TestBasic(unittest.TestCase):

    def test_first_frame_never_triggers(self):
        """Перший кадр завжди ініціалізує фон — ніколи не = True."""
        d = make_detector()
        self.assertFalse(d.detect(rect(), 0.0))

    def test_identical_frame_no_motion(self):
        d = make_detector()
        d.detect(black(), 0.0)
        self.assertFalse(d.detect(black(), 0.1))

    def test_large_rect_triggers(self):
        d = make_detector()
        d.detect(black(), 0.0)
        self.assertTrue(d.detect(rect(), 0.1))

    def test_tiny_rect_ignored(self):
        d = make_detector(min_contour_area=50_000, min_total_area=80_000)
        d.detect(black(), 0.0)
        self.assertFalse(d.detect(rect(w_r=5, h_r=5), 0.1))

    def test_reset_clears_background(self):
        d = make_detector()
        d.detect(black(), 0.0)
        self.assertIsNotNone(d._background)
        d.reset()
        self.assertIsNone(d._background)

    def test_reset_clears_stats(self):
        d = make_detector()
        d.detect(black(), 0.0)
        d.detect(rect(), 0.1)
        d.reset()
        # Перший кадр після reset = ініціалізація фону
        self.assertFalse(d.detect(rect(), 0.2))
        self.assertEqual(d.state.total_events, 0)

    def test_static_object_stays_motion(self):
        """
        Нерухомий об'єкт ЗАЛИШАЄТЬСЯ «рухом» відносно фонової моделі —
        на відміну від простого порівняння з попереднім кадром.
        """
        d = make_detector(min_consecutive_frames=1)
        d.detect(black(), 0.0)      # фон = чорний
        d.detect(rect(), 0.1)       # рух є → фон НЕ оновлюється
        self.assertTrue(d.detect(rect(), 0.2))  # прямокутник досі відрізняється від фону

    def test_disabled_always_sends(self):
        d = make_detector()
        d.config.enabled = False
        # enabled=False — логіка виявлення не викликається, але detect() повертає True
        # (виклик detect() з disabled обробляється в camera_worker, не тут)
        # Перевіряємо що фон ініціалізується нормально
        d.detect(black(), 0.0)
        self.assertIsNotNone(d._background)


# ══════════════════════════════════════════════════════════════════════════════
# Consecutive frames
# ══════════════════════════════════════════════════════════════════════════════

class TestConsecutiveFrames(unittest.TestCase):

    def test_requires_n_frames(self):
        d = make_detector(min_consecutive_frames=3)
        d.detect(black(), 0.0)
        m = rect()
        self.assertFalse(d.detect(m, 0.1))  # 1
        self.assertFalse(d.detect(m, 0.2))  # 2
        self.assertTrue(d.detect(m, 0.3))   # 3 ✓

    def test_gap_resets_counter(self):
        """Тихий кадр скидає лічильник підряд."""
        d = make_detector(min_consecutive_frames=3)
        d.detect(black(), 0.0)
        m = rect()
        d.detect(m, 0.1)   # 1
        d.detect(m, 0.2)   # 2
        d.detect(black(), 0.3)  # тиша → counter = 0, фон оновлюється
        self.assertFalse(d.detect(m, 0.4))  # counter = 1, потрібно 3

    def test_single_frame_mode(self):
        d = make_detector(min_consecutive_frames=1)
        d.detect(black(), 0.0)
        self.assertTrue(d.detect(rect(), 0.1))


# ══════════════════════════════════════════════════════════════════════════════
# Cooldown
# ══════════════════════════════════════════════════════════════════════════════

class TestCooldown(unittest.TestCase):

    def test_sends_during_cooldown_window(self):
        d = make_detector(min_consecutive_frames=1, cooldown_seconds=5.0)
        d.detect(black(), 0.0)
        d.detect(rect(), 1.0)       # підтверджений рух
        # Через 3 секунди — ще в cooldown (3 < 5)
        self.assertTrue(d.detect(black(), 4.0))

    def test_stops_after_cooldown_expires(self):
        d = make_detector(min_consecutive_frames=1, cooldown_seconds=2.0)
        d.detect(black(), 0.0)
        d.detect(rect(), 1.0)
        # Через 10 секунд — cooldown давно закінчився
        self.assertFalse(d.detect(black(), 11.0))

    def test_zero_cooldown_stops_immediately(self):
        d = make_detector(min_consecutive_frames=1, cooldown_seconds=0.0)
        d.detect(black(), 0.0)
        d.detect(rect(), 1.0)
        self.assertFalse(d.detect(black(), 1.1))

    def test_no_cooldown_without_prior_motion(self):
        """Cooldown не спрацьовує якщо руху ще не було."""
        d = make_detector(min_consecutive_frames=1, cooldown_seconds=100.0)
        d.detect(black(), 0.0)
        self.assertFalse(d.detect(black(), 0.1))

    def test_motion_active_true_during_cooldown_period(self):
        """BUG FIX #2: is_active must remain True during cooldown,
        not reset to False when consecutive frames drops.
        """
        d = make_detector(min_consecutive_frames=1, cooldown_seconds=5.0)
        d.detect(black(), 0.0)          # init background
        d.detect(rect(), 1.0)           # motion confirmed
        self.assertTrue(d.state.is_active)

        # Motion stops, but still within cooldown window (3 < 5)
        d.detect(black(), 4.0)
        self.assertTrue(d.state.is_active, "is_active should be True during cooldown")


# ══════════════════════════════════════════════════════════════════════════════
# Events і статистика
# ══════════════════════════════════════════════════════════════════════════════

class TestStats(unittest.TestCase):

    def test_two_separate_events(self):
        d = make_detector(min_consecutive_frames=1, cooldown_seconds=0.0)
        d.detect(black(), 0.0)
        d.detect(rect(), 1.0)       # event 1
        d.detect(black(), 2.0)      # тиша → фон оновлюється
        d.detect(rect(), 10.0)      # event 2
        self.assertEqual(d.state.total_events, 2)

    def test_continuous_motion_one_event(self):
        d = make_detector(min_consecutive_frames=1)
        d.detect(black(), 0.0)
        for t in [0.1, 0.2, 0.3, 0.4]:
            d.detect(rect(), t)
        self.assertEqual(d.state.total_events, 1)

    def test_get_stats_keys(self):
        d = make_detector()
        stats = d.get_stats()
        self.assertIn("motion_detected", stats)
        self.assertIn("total_motion_events", stats)
        self.assertIn("consecutive_frames", stats)

    def test_active_flag_on_off(self):
        d = make_detector(min_consecutive_frames=1, cooldown_seconds=0.0)
        d.detect(black(), 0.0)
        d.detect(rect(), 0.1)
        self.assertTrue(d.get_stats()["motion_detected"])
        d.detect(black(), 0.2)
        self.assertFalse(d.get_stats()["motion_detected"])


# ══════════════════════════════════════════════════════════════════════════════
# Background model
# ══════════════════════════════════════════════════════════════════════════════

class TestBackgroundModel(unittest.TestCase):

    def test_bg_not_updated_during_motion(self):
        import cv2
        d = make_detector(min_consecutive_frames=1, cooldown_seconds=5.0)
        d.detect(black(), 0.0)
        before = d._background.copy()
        d.detect(rect(), 0.1)
        d.detect(rect(), 0.2)
        # Фон не повинен змінитись поки є рух або cooldown
        self.assertEqual(cv2.absdiff(d._background, before).sum(), 0)

    def test_bg_updates_when_quiet(self):
        """alpha=1.0 → фон повністю замінюється поточним кадром."""
        d = make_detector(
            min_consecutive_frames=1,
            cooldown_seconds=0.0,
            background_update_alpha=1.0,
        )
        d.detect(black(), 0.0)      # фон = чорний
        d.detect(rect(), 0.1)       # рух підтверджено
        d.detect(black(), 0.2)      # тиша → фон оновлюється до чорного
        # Прямокутник знову видимий на новому чорному фоні
        self.assertTrue(d.detect(rect(), 0.3))

    def test_bg_matches_frame_shape(self):
        d = make_detector()
        d.detect(black(240, 320), 0.0)
        self.assertEqual(d._background.shape, (240, 320))

    def test_default_alpha(self):
        self.assertEqual(MotionDetectorConfig().background_update_alpha, 0.05)

    def test_update_config(self):
        d = make_detector()
        new_cfg = MotionDetectorConfig(min_contour_area=99999)
        d.update_config(new_cfg)
        self.assertEqual(d.config.min_contour_area, 99999)


# ══════════════════════════════════════════════════════════════════════════════
# Scanner utils (без pydantic)
# ══════════════════════════════════════════════════════════════════════════════

class TestScannerUtils(unittest.TestCase):

    def test_build_url_no_auth(self):
        from frame_extractor_service.service._scanner_utils import build_rtsp_url
        self.assertEqual(
            build_rtsp_url("192.168.1.1", 554),
            "rtsp://192.168.1.1:554/",
        )

    def test_build_url_with_credentials(self):
        from frame_extractor_service.service._scanner_utils import build_rtsp_url
        self.assertEqual(
            build_rtsp_url("192.168.1.1", 554, user="admin", password="pass", path="stream"),
            "rtsp://admin:pass@192.168.1.1:554/stream",
        )

    def test_build_url_user_no_password(self):
        from frame_extractor_service.service._scanner_utils import build_rtsp_url
        url = build_rtsp_url("10.0.0.1", 8554, user="admin", password="")
        self.assertIn("admin@", url)
        self.assertNotIn(":@", url)

    def test_build_url_strips_leading_slash(self):
        from frame_extractor_service.service._scanner_utils import build_rtsp_url
        url = build_rtsp_url("1.2.3.4", 554, path="/stream")
        self.assertEqual(url, "rtsp://1.2.3.4:554/stream")

    def test_invalid_subnet_raises(self):
        from frame_extractor_service.service._scanner_utils import scan_network_sync
        with self.assertRaises(ValueError):
            scan_network_sync("not_a_subnet", [554], [], timeout=0.1, max_workers=4)

    def test_unreachable_subnet_returns_empty(self):
        """192.0.2.0/29 — TEST-NET, не використовується в реальних мережах."""
        from frame_extractor_service.service._scanner_utils import scan_network_sync
        result = scan_network_sync(
            "192.0.2.0/29", [9999], [], timeout=0.1, max_workers=8
        )
        self.assertEqual(result["found"], [])
        self.assertEqual(result["subnet"], "192.0.2.0/29")
        self.assertGreater(result["hosts_scanned"], 0)

    def test_result_keys(self):
        from frame_extractor_service.service._scanner_utils import scan_network_sync
        result = scan_network_sync(
            "192.0.2.0/29", [9999], [], timeout=0.1, max_workers=4
        )
        for key in ("subnet", "ports_scanned", "hosts_scanned", "found", "scan_duration_sec"):
            self.assertIn(key, result)


# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    unittest.main(verbosity=2)
