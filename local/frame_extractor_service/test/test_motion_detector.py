"""
Тести для MotionDetector (unittest).
Детектор використовує background model — порівнює з фоном, не з попереднім кадром.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import cv2
import unittest
import numpy as np
from motion_detector import MotionDetector, MotionConfig


def black_frame(h=480, w=640):
    return np.zeros((h, w, 3), dtype=np.uint8)

def frame_with_rect(x, y, w_r, h_r, frame_h=480, frame_w=640):
    f = black_frame(frame_h, frame_w)
    f[y:y+h_r, x:x+w_r] = 255
    return f

def make_detector(**kwargs) -> MotionDetector:
    """Детектор з мінімальними порогами і instant bg update (alpha=1.0) для тестів."""
    cfg = MotionConfig(
        min_contour_area=kwargs.pop("min_contour_area", 500),
        min_total_area=kwargs.pop("min_total_area", 800),
        min_solidity=kwargs.pop("min_solidity", 0.3),
        min_consecutive_frames=kwargs.pop("min_consecutive_frames", 1),
        cooldown_seconds=kwargs.pop("cooldown_seconds", 0.0),
        blur_size=kwargs.pop("blur_size", 3),
        diff_threshold=kwargs.pop("diff_threshold", 10),
        dilate_iterations=kwargs.pop("dilate_iterations", 1),
        # alpha=1.0: bg оновлюється МИТТЄВО → детерміністичні тести
        background_update_alpha=kwargs.pop("background_update_alpha", 1.0),
        **kwargs,
    )
    return MotionDetector(cfg)


class TestBasic(unittest.TestCase):

    def test_first_frame_always_false(self):
        """Перший кадр ініціалізує background — завжди False."""
        d = make_detector()
        self.assertFalse(d.detect(frame_with_rect(100, 100, 200, 150), 0.0))

    def test_identical_to_background_no_motion(self):
        """Кадр ідентичний background → рух відсутній."""
        d = make_detector()
        bg = black_frame()
        d.detect(bg, 0.0)
        self.assertFalse(d.detect(bg, 0.1))

    def test_large_object_vs_background_triggers_motion(self):
        """Великий об'єкт з'являється на чистому фоні → рух."""
        d = make_detector()
        d.detect(black_frame(), 0.0)
        self.assertTrue(d.detect(frame_with_rect(100, 100, 200, 150), 0.1))

    def test_object_stays_on_screen_still_detected(self):
        """
        Нерухомий об'єкт ЗАЛИШАЄТЬСЯ рухом відносно background.
        Ключова перевага над prev-frame підходом.
        """
        d = make_detector(min_consecutive_frames=1, cooldown_seconds=0.0)
        d.detect(black_frame(), 0.0)
        moved = frame_with_rect(100, 100, 200, 150)
        d.detect(moved, 0.1)  # підтверджено — bg НЕ оновлюється
        # Той самий кадр: obj стоїть, але відносно bg він ДОСІ є рухом
        self.assertTrue(d.detect(moved, 0.2))

    def test_small_object_ignored(self):
        """Малий об'єкт (листя) нижче порогу → False."""
        d = make_detector(min_contour_area=5000, min_total_area=8000)
        d.detect(black_frame(), 0.0)
        self.assertFalse(d.detect(frame_with_rect(100, 100, 10, 10), 0.1))

    def test_reset_clears_background(self):
        """reset() обнуляє _background."""
        d = make_detector()
        d.detect(black_frame(), 0.0)
        self.assertIsNotNone(d._background)
        d.reset()
        self.assertIsNone(d._background)

    def test_reset_clears_all_state(self):
        """reset() скидає весь стан."""
        d = make_detector()
        d.detect(black_frame(), 0.0)
        d.detect(frame_with_rect(100, 100, 200, 150), 0.1)
        d.reset()
        # Після reset — перший кадр знову ініціалізує bg → False
        self.assertFalse(d.detect(frame_with_rect(100, 100, 200, 150), 0.2))
        self.assertEqual(d.state.total_events, 0)
        self.assertEqual(d.state.consecutive_frames, 0)
        self.assertEqual(d.state.last_confirmed_time, 0.0)


class TestConsecutive(unittest.TestCase):

    def test_needs_n_frames_before_confirm(self):
        """min_consecutive_frames=3: перші 2 → False, третій → True."""
        d = make_detector(min_consecutive_frames=3, cooldown_seconds=0.0)
        d.detect(black_frame(), 0.0)  # bg = black
        moved = frame_with_rect(100, 100, 200, 150)
        # bg не оновлюється поки should_send=False (consecutive < 3)
        self.assertFalse(d.detect(moved, 0.1))   # consec=1
        self.assertFalse(d.detect(moved, 0.2))   # consec=2
        self.assertTrue(d.detect(moved, 0.3))    # consec=3 → підтверджено

    def test_gap_resets_consecutive_counter(self):
        """Тихий кадр між рухами → consecutive=0, bg оновлюється (alpha=1.0 → миттєво)."""
        d = make_detector(min_consecutive_frames=3, cooldown_seconds=0.0)
        d.detect(black_frame(), 0.0)
        moved = frame_with_rect(100, 100, 200, 150)
        d.detect(moved, 0.1)   # consec=1
        d.detect(moved, 0.2)   # consec=2
        # bg кадр: cooldown=0, should_send=False → bg оновлюється миттєво (alpha=1.0)
        d.detect(black_frame(), 0.3)   # consec=0, bg стає black
        # Тепер moved знову є рухом, але consecutive=1 → False
        self.assertFalse(d.detect(moved, 0.4))

    def test_min_consecutive_1_reacts_immediately(self):
        d = make_detector(min_consecutive_frames=1, cooldown_seconds=0.0)
        d.detect(black_frame(), 0.0)
        self.assertTrue(d.detect(frame_with_rect(100, 100, 200, 150), 0.1))


class TestCooldown(unittest.TestCase):

    def test_sends_during_cooldown(self):
        """Після руху продовжуємо надсилати cooldown_seconds."""
        d = make_detector(min_consecutive_frames=1, cooldown_seconds=5.0)
        d.detect(black_frame(), 0.0)
        d.detect(frame_with_rect(100, 100, 200, 150), 1.0)
        # 3с після руху → ще в cooldown (5с)
        self.assertTrue(d.detect(black_frame(), 4.0))

    def test_stops_after_cooldown_expires(self):
        """Після cooldown_seconds без руху — зупиняємо."""
        d = make_detector(min_consecutive_frames=1, cooldown_seconds=2.0)
        d.detect(black_frame(), 0.0)
        d.detect(frame_with_rect(100, 100, 200, 150), 1.0)
        # 9с > cooldown 2с → bg вже оновився (alpha=1.0) → False
        self.assertFalse(d.detect(black_frame(), 10.0))

    def test_zero_cooldown_stops_immediately(self):
        """cooldown=0: після тихого кадру одразу False."""
        d = make_detector(min_consecutive_frames=1, cooldown_seconds=0.0)
        d.detect(black_frame(), 0.0)
        d.detect(frame_with_rect(100, 100, 200, 150), 1.0)
        # Тихий bg кадр: should_send=False, bg оновлюється → False
        self.assertFalse(d.detect(black_frame(), 1.1))

    def test_cooldown_extended_by_new_motion(self):
        """Новий рух під час cooldown → продовжує відлік."""
        d = make_detector(min_consecutive_frames=1, cooldown_seconds=3.0)
        d.detect(black_frame(), 0.0)
        moved = frame_with_rect(100, 100, 200, 150)
        d.detect(moved, 1.0)   # last_confirmed=1.0
        d.detect(moved, 3.5)   # новий рух, last_confirmed=3.5
        # 2.5с після 3.5 → ще в cooldown (3с)
        self.assertTrue(d.detect(black_frame(), 6.0))

    def test_no_cooldown_without_prior_motion(self):
        """Якщо руху ніколи не було — cooldown не активний."""
        d = make_detector(min_consecutive_frames=1, cooldown_seconds=5.0)
        d.detect(black_frame(), 0.0)
        self.assertFalse(d.detect(black_frame(), 0.1))


class TestStats(unittest.TestCase):

    def test_counts_separate_motion_events(self):
        """Дві окремі події руху → total_events=2."""
        d = make_detector(min_consecutive_frames=1, cooldown_seconds=0.0)
        d.detect(black_frame(), 0.0)
        moved = frame_with_rect(100, 100, 200, 150)
        # Подія 1
        d.detect(moved, 1.0)
        # bg кадр: cooldown=0 → bg оновлюється миттєво (alpha=1.0)
        d.detect(black_frame(), 2.0)
        # Подія 2
        d.detect(moved, 10.0)
        self.assertEqual(d.state.total_events, 2)

    def test_continuous_motion_is_one_event(self):
        """Безперервний рух = одна подія."""
        d = make_detector(min_consecutive_frames=1, cooldown_seconds=0.0)
        d.detect(black_frame(), 0.0)
        moved = frame_with_rect(100, 100, 200, 150)
        for t in [0.1, 0.2, 0.3, 0.4]:
            d.detect(moved, t)
        self.assertEqual(d.state.total_events, 1)

    def test_get_stats_required_keys(self):
        d = make_detector()
        stats = d.get_stats()
        self.assertIn("motion_detected", stats)
        self.assertIn("total_motion_events", stats)
        self.assertIn("consecutive_frames", stats)

    def test_motion_active_flag_lifecycle(self):
        """is_active: False → True при русі → False після тихого кадру."""
        d = make_detector(min_consecutive_frames=1, cooldown_seconds=0.0)
        d.detect(black_frame(), 0.0)
        d.detect(frame_with_rect(100, 100, 200, 150), 0.1)
        self.assertTrue(d.get_stats()["motion_detected"])
        d.detect(black_frame(), 0.2)
        self.assertFalse(d.get_stats()["motion_detected"])


class TestUpdateConfig(unittest.TestCase):

    def test_higher_threshold_blocks_motion(self):
        d = make_detector(min_consecutive_frames=1, cooldown_seconds=0.0)
        d.detect(black_frame(), 0.0)
        self.assertTrue(d.detect(frame_with_rect(100, 100, 200, 150), 0.1))

        d.reset()
        d.update_config(MotionConfig(
            min_contour_area=999999, min_total_area=999999,
            min_consecutive_frames=1, cooldown_seconds=0.0,
            blur_size=3, diff_threshold=10, dilate_iterations=1,
        ))
        d.detect(black_frame(), 1.0)
        self.assertFalse(d.detect(frame_with_rect(100, 100, 200, 150), 1.1))

    def test_update_preserves_stats(self):
        d = make_detector(min_consecutive_frames=1, cooldown_seconds=0.0)
        d.detect(black_frame(), 0.0)
        d.detect(frame_with_rect(100, 100, 200, 150), 1.0)
        events = d.state.total_events
        d.update_config(MotionConfig(cooldown_seconds=10.0))
        self.assertEqual(d.state.total_events, events)

    def test_disable_flag_stored(self):
        d = make_detector()
        d.update_config(MotionConfig(enabled=False))
        self.assertFalse(d.config.enabled)


class TestSolidity(unittest.TestCase):

    def test_solid_rectangle_passes_filter(self):
        """Суцільний прямокутник (solidity ≈ 1.0) проходить всі фільтри."""
        d = make_detector(min_solidity=0.5, min_consecutive_frames=1, cooldown_seconds=0.0)
        d.detect(black_frame(), 0.0)
        self.assertTrue(d.detect(frame_with_rect(50, 50, 300, 200), 0.1))


class TestBackgroundModel(unittest.TestCase):

    def test_background_not_updated_during_motion(self):
        """Background не змінюється поки є рух (should_send=True)."""
        d = make_detector(min_consecutive_frames=1, cooldown_seconds=5.0)
        d.detect(black_frame(), 0.0)
        bg_before = d._background.copy()

        moved = frame_with_rect(100, 100, 200, 150)
        d.detect(moved, 0.1)   # підтверджено
        d.detect(moved, 0.2)   # ще в русі

        diff = cv2.absdiff(d._background, bg_before)
        self.assertEqual(diff.sum(), 0)

    def test_background_updates_instantly_when_alpha_1(self):
        """З alpha=1.0 background оновлюється миттєво до нового кадру."""
        d = make_detector(min_consecutive_frames=1, cooldown_seconds=0.0, background_update_alpha=1.0)
        d.detect(black_frame(), 0.0)
        moved = frame_with_rect(100, 100, 200, 150)
        d.detect(moved, 0.1)       # рух → bg не оновлюється
        d.detect(black_frame(), 0.2)  # тиша → bg = black (alpha=1.0)
        # Тепер moved знову є рухом
        self.assertTrue(d.detect(moved, 0.3))

    def test_background_update_alpha_field_exists(self):
        """MotionConfig має поле background_update_alpha."""
        cfg = MotionConfig()
        self.assertTrue(hasattr(cfg, "background_update_alpha"))
        self.assertEqual(cfg.background_update_alpha, 0.05)


if __name__ == "__main__":
    unittest.main()
