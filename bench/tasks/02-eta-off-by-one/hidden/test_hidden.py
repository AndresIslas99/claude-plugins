"""Hidden acceptance tests for task 02: the ETA off-by-one."""

import unittest
from datetime import date

from transferlib import eta

MONDAY = date(2024, 3, 4)
FRIDAY = date(2024, 3, 8)


class ExactMultipleTests(unittest.TestCase):
    def test_one_day_of_data_takes_one_day(self) -> None:
        self.assertEqual(eta.transfer_business_days(500, "standard"), 1)
        self.assertEqual(eta.transfer_business_days(400, "bulk"), 1)
        self.assertEqual(eta.transfer_business_days(750, "priority"), 1)

    def test_several_whole_days(self) -> None:
        self.assertEqual(eta.transfer_business_days(1000, "standard"), 2)
        self.assertEqual(eta.transfer_business_days(2500, "standard"), 5)
        self.assertEqual(eta.transfer_business_days(1200, "bulk"), 3)
        self.assertEqual(eta.transfer_business_days(2250, "priority"), 3)

    def test_float_gigabytes_on_an_exact_multiple(self) -> None:
        self.assertEqual(eta.transfer_business_days(500.0, "standard"), 1)
        self.assertEqual(eta.transfer_business_days(1000.0), 2)

    def test_default_service_is_standard(self) -> None:
        self.assertEqual(eta.transfer_business_days(500), 1)


class PartlyUsedDayTests(unittest.TestCase):
    def test_a_partly_used_day_still_counts_as_a_whole_day(self) -> None:
        cases = [
            (0.5, "priority", 1),
            (1, "standard", 1),
            (499, "standard", 1),
            (500.5, "standard", 2),
            (501, "standard", 2),
            (999, "standard", 2),
            (1001, "standard", 3),
            (401, "bulk", 2),
            (751, "priority", 2),
        ]
        for gigabytes, service, days in cases:
            with self.subTest(gigabytes=gigabytes, service=service):
                self.assertEqual(eta.transfer_business_days(gigabytes, service), days)

    def test_the_result_is_an_int(self) -> None:
        self.assertIsInstance(eta.transfer_business_days(1000.0), int)
        self.assertIsInstance(eta.transfer_business_days(1000.5), int)


class DeliveryDateTests(unittest.TestCase):
    def test_the_reported_case(self) -> None:
        self.assertEqual(eta.estimate_delivery(MONDAY, 500), date(2024, 3, 5))
        self.assertEqual(eta.estimate_delivery(MONDAY, 500, "standard"), date(2024, 3, 5))

    def test_delivery_skips_the_weekend(self) -> None:
        self.assertEqual(eta.estimate_delivery(FRIDAY, 500), date(2024, 3, 11))
        self.assertEqual(eta.estimate_delivery(MONDAY, 2500), date(2024, 3, 11))
        self.assertEqual(eta.estimate_delivery(FRIDAY, 800, "bulk"), date(2024, 3, 12))

    def test_amounts_off_the_multiple_are_unchanged(self) -> None:
        self.assertEqual(eta.estimate_delivery(MONDAY, 650), date(2024, 3, 6))
        self.assertEqual(eta.estimate_delivery(date(2024, 3, 7), 650), date(2024, 3, 11))


class InputCheckTests(unittest.TestCase):
    def test_gigabytes_must_still_be_positive(self) -> None:
        for gigabytes in (0, -500):
            with self.assertRaisesRegex(ValueError, "gigabytes must be positive"):
                eta.transfer_business_days(gigabytes)

    def test_unknown_service_still_raises(self) -> None:
        with self.assertRaisesRegex(ValueError, "unknown service: tape"):
            eta.transfer_business_days(100, "tape")


if __name__ == "__main__":
    unittest.main()
