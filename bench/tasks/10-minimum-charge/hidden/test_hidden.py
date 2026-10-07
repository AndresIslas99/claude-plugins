"""Hidden acceptance tests for task 10: the new minimum charge for every service."""

import unittest
from decimal import Decimal

from freightlib import quotes, rates

D = Decimal
SERVICES = ("standard", "bulk", "expedited")


class MinimumChargeValueTests(unittest.TestCase):
    def test_the_minimum_charge_is_95(self) -> None:
        self.assertEqual(rates.MINIMUM_CHARGE, D("95.00"))
        self.assertIsInstance(rates.MINIMUM_CHARGE, Decimal)


class ShortHaulTests(unittest.TestCase):
    def test_short_standard_and_bulk_hauls_pay_the_new_minimum(self) -> None:
        # 45 standard miles = 94.50 and 57 bulk miles = 94.05, both under 95.
        self.assertEqual(rates.calc_rate(10, "standard"), D("95.00"))
        self.assertEqual(rates.calc_rate(45, "standard"), D("95.00"))
        self.assertEqual(rates.calc_rate(10, "bulk"), D("95.00"))
        self.assertEqual(rates.calc_rate(57, "bulk"), D("95.00"))

    def test_short_expedited_hauls_pay_the_minimum_too(self) -> None:
        # The reported case: 10 expedited miles came out at 34.00.
        self.assertEqual(rates.calc_rate(10, "expedited"), D("95.00"))
        self.assertEqual(rates.calc_rate(1, "expedited"), D("95.00"))
        self.assertEqual(rates.calc_rate(0.5, "expedited"), D("95.00"))
        self.assertEqual(rates.calc_rate(D("27.9"), "expedited"), D("95.00"))
        self.assertEqual(rates.calc_rate(27, "expedited"), D("95.00"))

    def test_the_result_has_two_decimal_places(self) -> None:
        for service in SERVICES:
            with self.subTest(service=service):
                self.assertEqual(str(rates.calc_rate(10, service)), "95.00")

    def test_no_service_is_ever_charged_less_than_the_minimum(self) -> None:
        for service in SERVICES:
            for miles in range(1, 121):
                with self.subTest(service=service, miles=miles):
                    self.assertGreaterEqual(rates.calc_rate(miles, service), rates.MINIMUM_CHARGE)


class AboveTheMinimumTests(unittest.TestCase):
    def test_charges_above_the_minimum_are_unchanged(self) -> None:
        cases = [
            (46, "standard", "96.60"),
            (58, "bulk", "95.70"),
            (28, "expedited", "95.20"),
            (50, "standard", "105.00"),
            (100, "standard", "210.00"),
            (100, "bulk", "165.00"),
            (100, "expedited", "340.00"),
        ]
        for miles, service, expected in cases:
            with self.subTest(miles=miles, service=service):
                self.assertEqual(rates.calc_rate(miles, service), D(expected))

    def test_rounding_above_the_minimum_is_unchanged(self) -> None:
        self.assertEqual(rates.calc_rate(D("60.5"), "bulk"), D("99.83"))
        self.assertEqual(rates.calc_rate(60.5, "bulk"), D("99.83"))

    def test_input_errors_are_unchanged(self) -> None:
        with self.assertRaisesRegex(ValueError, "^miles must be positive$"):
            rates.calc_rate(0, "expedited")
        with self.assertRaisesRegex(ValueError, "^unknown service: air$"):
            rates.calc_rate(10, "air")


class BuiltOnTheRateTests(unittest.TestCase):
    def test_round_trips_follow_the_new_minimum(self) -> None:
        # The outbound charge is 95.00 and the return leg is 60% of it.
        for service in SERVICES:
            with self.subTest(service=service):
                self.assertEqual(rates.round_trip_rate(10, service), D("152.00"))
        self.assertEqual(rates.round_trip_rate(100, "standard"), D("336.00"))

    def test_short_quotes_use_the_minimum_for_every_service(self) -> None:
        for service in SERVICES:
            with self.subTest(service=service):
                quote = quotes.build_quote(10, 500, service)
                self.assertEqual(quote.lines[0].amount, D("95.00"))
                self.assertEqual(quote.total, D("95.00"))

    def test_surcharges_are_added_on_top_of_the_minimum(self) -> None:
        quote = quotes.build_quote(10, 500, "expedited", ["liftgate", "hazmat"])
        self.assertEqual(quote.lines[0].description, "Line haul (expedited)")
        self.assertEqual(quote.lines[0].amount, D("95.00"))
        self.assertEqual(quote.total, D("205.00"))

    def test_long_quotes_are_unchanged(self) -> None:
        self.assertEqual(quotes.build_quote(100, 20000, "expedited").total, D("340.00"))


if __name__ == "__main__":
    unittest.main()
