import unittest
from decimal import Decimal

from transferlib.rates import calc_rate, per_gb_rate, replicated_rate


class PerGbRateTests(unittest.TestCase):
    def test_known_services(self) -> None:
        self.assertEqual(per_gb_rate("standard"), Decimal("2.10"))
        self.assertEqual(per_gb_rate("bulk"), Decimal("1.65"))
        self.assertEqual(per_gb_rate("priority"), Decimal("3.40"))

    def test_unknown_service_raises(self) -> None:
        with self.assertRaisesRegex(ValueError, "unknown service: tape"):
            per_gb_rate("tape")


class CalcRateTests(unittest.TestCase):
    def test_standard_large_transfer(self) -> None:
        self.assertEqual(calc_rate(100, "standard"), Decimal("210.00"))

    def test_service_defaults_to_standard(self) -> None:
        self.assertEqual(calc_rate(100), calc_rate(100, "standard"))

    def test_bulk_large_transfer(self) -> None:
        self.assertEqual(calc_rate(100, "bulk"), Decimal("165.00"))

    def test_priority_large_transfer(self) -> None:
        self.assertEqual(calc_rate(100, "priority"), Decimal("340.00"))

    def test_small_transfer_pays_minimum(self) -> None:
        self.assertEqual(calc_rate(10, "standard"), Decimal("85.00"))

    def test_minimum_does_not_lower_a_larger_charge(self) -> None:
        self.assertEqual(calc_rate(50, "standard"), Decimal("105.00"))

    def test_rounds_half_up_to_cents(self) -> None:
        # 60.5 GB x 1.65 = 99.825
        self.assertEqual(calc_rate(Decimal("60.5"), "bulk"), Decimal("99.83"))

    def test_float_gigabytes(self) -> None:
        self.assertEqual(calc_rate(60.5, "bulk"), Decimal("99.83"))

    def test_result_has_two_decimal_places(self) -> None:
        self.assertEqual(str(calc_rate(100)), "210.00")

    def test_gigabytes_must_be_positive(self) -> None:
        for gigabytes in (0, -5):
            with self.assertRaisesRegex(ValueError, "gigabytes must be positive"):
                calc_rate(gigabytes)

    def test_unknown_service_raises(self) -> None:
        with self.assertRaisesRegex(ValueError, "unknown service: tape"):
            calc_rate(100, "tape")


class ReplicatedRateTests(unittest.TestCase):
    def test_adds_the_second_copy(self) -> None:
        self.assertEqual(replicated_rate(100, "standard"), Decimal("336.00"))

    def test_rounds_to_cents(self) -> None:
        # 99.83 x 1.6 = 159.728
        self.assertEqual(replicated_rate(Decimal("60.5"), "bulk"), Decimal("159.73"))
