import unittest
from datetime import date

from freightlib.eta import (
    add_business_days,
    estimate_delivery,
    is_business_day,
    transit_business_days,
)

MONDAY = date(2024, 3, 4)
THURSDAY = date(2024, 3, 7)
FRIDAY = date(2024, 3, 8)
SATURDAY = date(2024, 3, 9)
NEXT_MONDAY = date(2024, 3, 11)


class BusinessDayTests(unittest.TestCase):
    def test_weekdays_are_business_days(self) -> None:
        for day in (MONDAY, THURSDAY, FRIDAY):
            self.assertTrue(is_business_day(day))

    def test_weekend_days_are_not(self) -> None:
        self.assertFalse(is_business_day(SATURDAY))
        self.assertFalse(is_business_day(date(2024, 3, 10)))


class AddBusinessDaysTests(unittest.TestCase):
    def test_within_a_week(self) -> None:
        self.assertEqual(add_business_days(MONDAY, 3), THURSDAY)

    def test_skips_the_weekend(self) -> None:
        self.assertEqual(add_business_days(FRIDAY, 1), NEXT_MONDAY)

    def test_starting_on_a_weekend(self) -> None:
        self.assertEqual(add_business_days(SATURDAY, 1), NEXT_MONDAY)

    def test_across_two_weeks(self) -> None:
        self.assertEqual(add_business_days(date(2024, 3, 6), 7), date(2024, 3, 15))

    def test_zero_days_returns_the_start(self) -> None:
        self.assertEqual(add_business_days(SATURDAY, 0), SATURDAY)

    def test_negative_days_raises(self) -> None:
        with self.assertRaisesRegex(ValueError, "days must not be negative"):
            add_business_days(MONDAY, -1)


class TransitBusinessDaysTests(unittest.TestCase):
    def test_short_trip_takes_one_day(self) -> None:
        self.assertEqual(transit_business_days(120), 1)

    def test_partly_used_day_counts_as_a_whole_day(self) -> None:
        self.assertEqual(transit_business_days(650), 2)

    def test_service_changes_the_speed(self) -> None:
        self.assertEqual(transit_business_days(900, "bulk"), 3)
        self.assertEqual(transit_business_days(1600, "expedited"), 3)

    def test_input_is_validated(self) -> None:
        with self.assertRaisesRegex(ValueError, "miles must be positive"):
            transit_business_days(0)
        with self.assertRaisesRegex(ValueError, "unknown service: air"):
            transit_business_days(100, "air")


class EstimateDeliveryTests(unittest.TestCase):
    def test_midweek_pickup(self) -> None:
        self.assertEqual(estimate_delivery(MONDAY, 650), date(2024, 3, 6))

    def test_delivery_skips_the_weekend(self) -> None:
        self.assertEqual(estimate_delivery(THURSDAY, 650), NEXT_MONDAY)

    def test_expedited_service(self) -> None:
        self.assertEqual(estimate_delivery(MONDAY, 1600, "expedited"), THURSDAY)
