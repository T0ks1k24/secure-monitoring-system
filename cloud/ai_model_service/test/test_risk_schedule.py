"""
Тести для RiskScheduleEvaluator та reduce_risk.
Запуск: python3 -m unittest tests/test_risk_schedule.py -v
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import unittest
from datetime import datetime, time as dtime


# ── Ізольований імпорт без ultralytics/fastapi ────────────────────────────────
from schemas.events import RiskLevel, RiskSchedule, EventType, ZoneType, Zone, ZoneRule
from services.risk_engine import (
    reduce_risk, RiskScheduleEvaluator, RiskEngine, _RISK_ORDER
)


def _now(hour: int, minute: int = 0, weekday: int = 0) -> datetime:
    """Створює datetime з заданим часом і днем тижня (0=пн)."""
    # weekday(): 0=пн. Починаємо з 2025-01-06 (пн) і додаємо weekday днів.
    from datetime import timedelta
    base = datetime(2025, 1, 6, hour, minute)  # це понеділок
    return base + timedelta(days=weekday)


def _make_zone(schedules=None) -> Zone:
    return Zone(
        id="z1", camera_id="cam1", name="Test Zone",
        zone_type=ZoneType.RESTRICTED,
        polygon=[[0,0],[1,0],[1,1],[0,1]],
        risk_schedules=schedules or [],
    )


def _make_schedule(**kwargs) -> RiskSchedule:
    defaults = dict(time_start="08:00", time_end="17:00", reduce_by=1)
    defaults.update(kwargs)
    return RiskSchedule(**defaults)


# ─────────────────────────────────────────────────────────────────────────────

class TestReduceRisk(unittest.TestCase):

    def test_reduce_by_1(self):
        self.assertEqual(reduce_risk(RiskLevel.CRITICAL, 1), RiskLevel.HIGH)
        self.assertEqual(reduce_risk(RiskLevel.HIGH,     1), RiskLevel.MEDIUM)
        self.assertEqual(reduce_risk(RiskLevel.MEDIUM,   1), RiskLevel.LOW)
        self.assertEqual(reduce_risk(RiskLevel.LOW,      1), RiskLevel.LOW)   # мінімум

    def test_reduce_by_2(self):
        self.assertEqual(reduce_risk(RiskLevel.CRITICAL, 2), RiskLevel.MEDIUM)
        self.assertEqual(reduce_risk(RiskLevel.HIGH,     2), RiskLevel.LOW)
        self.assertEqual(reduce_risk(RiskLevel.MEDIUM,   2), RiskLevel.LOW)

    def test_reduce_by_3_max_suppression(self):
        self.assertEqual(reduce_risk(RiskLevel.CRITICAL, 3), RiskLevel.LOW)
        self.assertEqual(reduce_risk(RiskLevel.HIGH,     3), RiskLevel.LOW)

    def test_low_never_goes_below_low(self):
        self.assertEqual(reduce_risk(RiskLevel.LOW, 5), RiskLevel.LOW)


class TestRiskScheduleEvaluator(unittest.TestCase):

    def setUp(self):
        self.ev = RiskScheduleEvaluator()

    # ── Базові вікна ──────────────────────────────────────────────

    def test_inside_window(self):
        s = _make_schedule(time_start="08:00", time_end="17:00")
        self.assertIsNotNone(self.ev.get_active_schedule([s], _now(12, 0)))

    def test_before_window(self):
        s = _make_schedule(time_start="08:00", time_end="17:00")
        self.assertIsNone(self.ev.get_active_schedule([s], _now(7, 59)))

    def test_after_window(self):
        s = _make_schedule(time_start="08:00", time_end="17:00")
        self.assertIsNone(self.ev.get_active_schedule([s], _now(17, 0)))  # end exclusive

    def test_exact_start(self):
        s = _make_schedule(time_start="08:00", time_end="17:00")
        self.assertIsNotNone(self.ev.get_active_schedule([s], _now(8, 0)))

    def test_one_minute_before_end(self):
        s = _make_schedule(time_start="08:00", time_end="17:00")
        self.assertIsNotNone(self.ev.get_active_schedule([s], _now(16, 59)))

    def test_no_schedules_returns_none(self):
        self.assertIsNone(self.ev.get_active_schedule([], _now(12, 0)))

    # ── Нічне вікно (перетин північ) ──────────────────────────────

    def test_night_window_before_midnight(self):
        s = _make_schedule(time_start="22:00", time_end="06:00")
        self.assertIsNotNone(self.ev.get_active_schedule([s], _now(23, 30)))

    def test_night_window_after_midnight(self):
        s = _make_schedule(time_start="22:00", time_end="06:00")
        self.assertIsNotNone(self.ev.get_active_schedule([s], _now(3, 0)))

    def test_night_window_during_day_is_inactive(self):
        s = _make_schedule(time_start="22:00", time_end="06:00")
        self.assertIsNone(self.ev.get_active_schedule([s], _now(12, 0)))

    def test_night_window_exactly_at_end_is_inactive(self):
        s = _make_schedule(time_start="22:00", time_end="06:00")
        self.assertIsNone(self.ev.get_active_schedule([s], _now(6, 0)))

    # ── Фільтр по днях тижня ──────────────────────────────────────

    def test_weekdays_only_active_on_monday(self):
        s = _make_schedule(days=[0, 1, 2, 3, 4])  # пн–пт
        self.assertIsNotNone(self.ev.get_active_schedule([s], _now(12, 0, weekday=0)))

    def test_weekdays_only_inactive_on_saturday(self):
        s = _make_schedule(days=[0, 1, 2, 3, 4])
        self.assertIsNone(self.ev.get_active_schedule([s], _now(12, 0, weekday=5)))

    def test_weekdays_only_inactive_on_sunday(self):
        s = _make_schedule(days=[0, 1, 2, 3, 4])
        self.assertIsNone(self.ev.get_active_schedule([s], _now(12, 0, weekday=6)))

    def test_weekend_only_active_on_saturday(self):
        s = _make_schedule(days=[5, 6])
        self.assertIsNotNone(self.ev.get_active_schedule([s], _now(12, 0, weekday=5)))

    def test_weekend_only_inactive_on_monday(self):
        s = _make_schedule(days=[5, 6])
        self.assertIsNone(self.ev.get_active_schedule([s], _now(12, 0, weekday=0)))

    def test_none_days_means_every_day(self):
        s = _make_schedule(days=None)
        for wd in range(7):
            self.assertIsNotNone(
                self.ev.get_active_schedule([s], _now(12, 0, weekday=wd)),
                f"Should be active on weekday {wd}"
            )

    # ── Кілька розкладів — береться max reduce_by ─────────────────

    def test_multiple_schedules_takes_max_reduce(self):
        s1 = _make_schedule(reduce_by=1)  # обидва активні
        s2 = _make_schedule(reduce_by=2)
        result = self.ev.get_active_schedule([s1, s2], _now(12, 0))
        self.assertEqual(result.reduce_by, 2)

    def test_only_active_schedule_returned(self):
        s_active   = _make_schedule(time_start="08:00", time_end="17:00", reduce_by=2)
        s_inactive = _make_schedule(time_start="18:00", time_end="23:00", reduce_by=3)
        result = self.ev.get_active_schedule([s_active, s_inactive], _now(12, 0))
        self.assertEqual(result.reduce_by, 2)

    def test_no_active_schedules_returns_none(self):
        s1 = _make_schedule(time_start="08:00", time_end="10:00")
        s2 = _make_schedule(time_start="14:00", time_end="16:00")
        self.assertIsNone(self.ev.get_active_schedule([s1, s2], _now(12, 0)))

    # ── Поле label ────────────────────────────────────────────────

    def test_label_preserved(self):
        s = _make_schedule(label="Робоча зміна А")
        result = self.ev.get_active_schedule([s], _now(12, 0))
        self.assertEqual(result.label, "Робоча зміна А")


class TestRiskEngineApplySchedule(unittest.TestCase):
    """Тести _apply_schedule безпосередньо."""

    def setUp(self):
        self.engine = RiskEngine()

    def _zone_with_schedule(self, reduce_by=1, active=True) -> Zone:
        if active:
            s = _make_schedule(reduce_by=reduce_by)
        else:
            s = _make_schedule(time_start="23:00", time_end="23:01", reduce_by=reduce_by)
        return _make_zone(schedules=[s])

    # ── Зброя ніколи не знижується ────────────────────────────────

    def test_weapon_never_reduced(self):
        zone = self._zone_with_schedule(reduce_by=3)
        level, sched = self.engine._apply_schedule(
            EventType.WEAPON_DETECTED, RiskLevel.CRITICAL, zone, _now(12, 0)
        )
        self.assertEqual(level, RiskLevel.CRITICAL)
        self.assertIsNone(sched)

    def test_weapon_never_reduced_even_with_multiple_schedules(self):
        schedules = [_make_schedule(reduce_by=i) for i in [1, 2, 3]]
        zone = _make_zone(schedules=schedules)
        level, _ = self.engine._apply_schedule(
            EventType.WEAPON_DETECTED, RiskLevel.CRITICAL, zone, _now(12, 0)
        )
        self.assertEqual(level, RiskLevel.CRITICAL)

    # ── Зональні події знижуються ─────────────────────────────────

    def test_zone_intrusion_reduced_by_1(self):
        zone = self._zone_with_schedule(reduce_by=1)
        level, sched = self.engine._apply_schedule(
            EventType.ZONE_INTRUSION, RiskLevel.HIGH, zone, _now(12, 0)
        )
        self.assertEqual(level, RiskLevel.MEDIUM)
        self.assertIsNotNone(sched)

    def test_zone_intrusion_reduced_by_2(self):
        zone = self._zone_with_schedule(reduce_by=2)
        level, _ = self.engine._apply_schedule(
            EventType.ZONE_INTRUSION, RiskLevel.HIGH, zone, _now(12, 0)
        )
        self.assertEqual(level, RiskLevel.LOW)

    def test_no_active_schedule_no_reduction(self):
        zone = self._zone_with_schedule(active=False)
        level, sched = self.engine._apply_schedule(
            EventType.ZONE_INTRUSION, RiskLevel.HIGH, zone, _now(12, 0)
        )
        self.assertEqual(level, RiskLevel.HIGH)
        self.assertIsNone(sched)

    def test_no_schedules_no_reduction(self):
        zone = _make_zone(schedules=[])
        level, sched = self.engine._apply_schedule(
            EventType.ZONE_INTRUSION, RiskLevel.HIGH, zone, _now(12, 0)
        )
        self.assertEqual(level, RiskLevel.HIGH)
        self.assertIsNone(sched)

    # ── Різні типи подій ──────────────────────────────────────────

    def test_loitering_reduced(self):
        zone = self._zone_with_schedule(reduce_by=1)
        level, _ = self.engine._apply_schedule(
            EventType.ZONE_LOITERING, RiskLevel.MEDIUM, zone, _now(12, 0)
        )
        self.assertEqual(level, RiskLevel.LOW)

    def test_running_via_reduce_for_zones(self):
        zone = self._zone_with_schedule(reduce_by=1)
        level = self.engine._reduce_for_zones(
            EventType.RUNNING_DETECTED, RiskLevel.MEDIUM, [zone], _now(12, 0)
        )
        self.assertEqual(level, RiskLevel.LOW)

    def test_abandoned_object_reduced(self):
        zone = self._zone_with_schedule(reduce_by=1)
        level = self.engine._reduce_for_zones(
            EventType.ABANDONED_OBJECT, RiskLevel.HIGH, [zone], _now(12, 0)
        )
        self.assertEqual(level, RiskLevel.MEDIUM)

    def test_no_zones_no_reduction(self):
        level = self.engine._reduce_for_zones(
            EventType.RUNNING_DETECTED, RiskLevel.MEDIUM, [], _now(12, 0)
        )
        self.assertEqual(level, RiskLevel.MEDIUM)


class TestRiskScheduleRealWorldScenarios(unittest.TestCase):
    """Реальні сценарії використання."""

    def setUp(self):
        self.engine = RiskEngine()
        self.ev = RiskScheduleEvaluator()

    def test_warehouse_worker_shift(self):
        """
        Склад: робоча зміна 06:00–14:00 в будні.
        Людина в restricted zone в 09:00 → MEDIUM (знижено з HIGH).
        """
        s = RiskSchedule(
            time_start="06:00", time_end="14:00",
            reduce_by=1, days=[0,1,2,3,4],
            label="Зміна А"
        )
        zone = _make_zone(schedules=[s])
        level, sched = self.engine._apply_schedule(
            EventType.ZONE_INTRUSION, RiskLevel.HIGH, zone,
            _now(9, 0, weekday=0)  # понеділок 09:00
        )
        self.assertEqual(level, RiskLevel.MEDIUM)
        self.assertEqual(sched.label, "Зміна А")

    def test_warehouse_worker_shift_outside_hours(self):
        """Та сама зона вночі — ризик залишається HIGH."""
        s = RiskSchedule(
            time_start="06:00", time_end="14:00",
            reduce_by=1, days=[0,1,2,3,4]
        )
        zone = _make_zone(schedules=[s])
        level, sched = self.engine._apply_schedule(
            EventType.ZONE_INTRUSION, RiskLevel.HIGH, zone,
            _now(23, 0, weekday=0)
        )
        self.assertEqual(level, RiskLevel.HIGH)
        self.assertIsNone(sched)

    def test_two_shifts_different_reduce(self):
        """
        Зона з двома змінами:
          Зміна А 06:00–14:00: reduce_by=1 (робочий рух очікується)
          Зміна Б 14:00–22:00: reduce_by=2 (підвищена активність)
        О 15:00 → береться max reduce_by=2.
        """
        shift_a = RiskSchedule(time_start="06:00", time_end="14:00",
                               reduce_by=1, label="Зміна А")
        shift_b = RiskSchedule(time_start="14:00", time_end="22:00",
                               reduce_by=2, label="Зміна Б")

        # О 15:00 — активна Зміна Б
        result = self.ev.get_active_schedule([shift_a, shift_b], _now(15, 0))
        self.assertIsNotNone(result)
        self.assertEqual(result.reduce_by, 2)
        self.assertEqual(result.label, "Зміна Б")

        # О 10:00 — активна Зміна А
        result = self.ev.get_active_schedule([shift_a, shift_b], _now(10, 0))
        self.assertIsNotNone(result)
        self.assertEqual(result.reduce_by, 1)
        self.assertEqual(result.label, "Зміна А")

    def test_weapon_during_shift_still_critical(self):
        """Зброя виявлена під час робочої зміни → завжди CRITICAL."""
        s = RiskSchedule(time_start="08:00", time_end="17:00", reduce_by=3)
        zone = _make_zone(schedules=[s])
        level, sched = self.engine._apply_schedule(
            EventType.WEAPON_DETECTED, RiskLevel.CRITICAL, zone,
            _now(12, 0)
        )
        self.assertEqual(level, RiskLevel.CRITICAL)
        self.assertIsNone(sched)

    def test_weekend_zone_3_cameras_independent(self):
        """
        3 незалежних зони з різними розкладами.
        Зона 1: пн–пт, Зона 2: пн–нд, Зона 3: тільки вихідні.
        """
        def make_zone_with_days(zone_id, days):
            return Zone(
                id=zone_id, camera_id="cam1", name=f"Zone {zone_id}",
                zone_type=ZoneType.RESTRICTED,
                polygon=[[0,0],[1,0],[1,1],[0,1]],
                risk_schedules=[RiskSchedule(
                    time_start="08:00", time_end="17:00",
                    reduce_by=1, days=days
                )],
            )

        zone1 = make_zone_with_days("z1", [0,1,2,3,4])   # будні
        zone2 = make_zone_with_days("z2", None)            # щодня
        zone3 = make_zone_with_days("z3", [5,6])           # вихідні

        saturday_noon = _now(12, 0, weekday=5)

        # Субота 12:00
        l1, _ = self.engine._apply_schedule(EventType.ZONE_INTRUSION, RiskLevel.HIGH, zone1, saturday_noon)
        l2, _ = self.engine._apply_schedule(EventType.ZONE_INTRUSION, RiskLevel.HIGH, zone2, saturday_noon)
        l3, _ = self.engine._apply_schedule(EventType.ZONE_INTRUSION, RiskLevel.HIGH, zone3, saturday_noon)

        self.assertEqual(l1, RiskLevel.HIGH)    # будні → субота неактивна
        self.assertEqual(l2, RiskLevel.MEDIUM)  # щодня → знижено
        self.assertEqual(l3, RiskLevel.MEDIUM)  # вихідні → знижено

    def test_risk_schedule_schema_validation(self):
        """Перевірка що schema приймає правильні дані."""
        s = RiskSchedule(
            time_start="08:30",
            time_end="12:30",
            reduce_by=2,
            days=[0, 1, 2, 3, 4],
            timezone="Europe/Kiev",
            label="Робоча зміна"
        )
        self.assertEqual(s.time_start, "08:30")
        self.assertEqual(s.reduce_by, 2)
        self.assertEqual(s.days, [0, 1, 2, 3, 4])

    def test_risk_schedule_reduce_by_bounds(self):
        """reduce_by: мінімум 1, максимум 3."""
        from pydantic import ValidationError
        with self.assertRaises(ValidationError):
            RiskSchedule(time_start="08:00", time_end="17:00", reduce_by=0)
        with self.assertRaises(ValidationError):
            RiskSchedule(time_start="08:00", time_end="17:00", reduce_by=4)

    def test_metadata_contains_schedule_info(self):
        """
        Перевіряємо що _apply_schedule повертає schedule object
        з якого можна зібрати metadata.
        """
        s = RiskSchedule(
            time_start="08:00", time_end="17:00",
            reduce_by=1, label="Денна зміна"
        )
        zone = _make_zone(schedules=[s])
        level, active = self.engine._apply_schedule(
            EventType.ZONE_INTRUSION, RiskLevel.HIGH, zone, _now(12, 0)
        )
        self.assertIsNotNone(active)
        self.assertEqual(active.label, "Денна зміна")
        self.assertEqual(active.reduce_by, 1)
        # metadata можна зібрати так:
        meta_label = active.label or f"{active.time_start}–{active.time_end}"
        self.assertEqual(meta_label, "Денна зміна")


if __name__ == "__main__":
    unittest.main(verbosity=2)
