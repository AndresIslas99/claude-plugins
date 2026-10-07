import unittest
from decimal import Decimal

from freightlib.rates import calc_rate, per_mile_rate, round_trip_rate


class PerMileRateTests(unittest.TestCase):
    def test_known_services(self) -> None:
        self.assertEqual(per_mile_rate("standard"), Decimal("2.10"))
        self.assertEqual(per_mile_rate("bulk"), Decimal("1.65"))
        self.assertEqual(per_mile_rate("expedited"), Decimal("3.40"))

    def test_unknown_service_raises(self) -> None:
        with self.assertRaisesRegex(ValueError, "unknown service: air"):
            per_mile_rate("air")


class CalcRateTests(unittest.TestCase):
    def test_standard_long_haul(self) -> None:
        self.assertEqual(calc_rate(100, "standard"), Decimal("210.00"))

    def test_service_defaults_to_standard(self) -> None:
        self.assertEqual(calc_rate(100), calc_rate(100, "standard"))

    def test_bulk_long_haul(self) -> None:
        self.assertEqual(calc_rate(100, "bulk"), Decimal("165.00"))

    def test_expedited_long_haul(self) -> None:
        self.assertEqual(calc_rate(100, "expedited"), Decimal("340.00"))

    def test_short_haul_pays_minimum(self) -> None:
        self.assertEqual(calc_rate(10, "standard"), Decimal("85.00"))

    def test_minimum_does_not_lower_a_larger_charge(self) -> None:
        self.assertEqual(calc_rate(50, "standard"), Decimal("105.00"))

    def test_rounds_half_up_to_cents(self) -> None:
        # 60.5 miles x 1.65 = 99.825
        self.assertEqual(calc_rate(Decimal("60.5"), "bulk"), Decimal("99.83"))

    def test_float_miles(self) -> None:
        self.assertEqual(calc_rate(60.5, "bulk"), Decimal("99.83"))

    def test_result_has_two_decimal_places(self) -> None:
        self.assertEqual(str(calc_rate(100)), "210.00")

    def test_miles_must_be_positive(self) -> None:
        for miles in (0, -5):
            with self.assertRaisesRegex(ValueError, "miles must be positive"):
                calc_rate(miles)

    def test_unknown_service_raises(self) -> None:
        with self.assertRaisesRegex(ValueError, "unknown service: air"):
            calc_rate(100, "air")


class RoundTripRateTests(unittest.TestCase):
    def test_adds_the_return_leg(self) -> None:
        self.assertEqual(round_trip_rate(100, "standard"), Decimal("336.00"))

    def test_rounds_to_cents(self) -> None:
        # 99.83 x 1.6 = 159.728
        self.assertEqual(round_trip_rate(Decimal("60.5"), "bulk"), Decimal("159.73"))
