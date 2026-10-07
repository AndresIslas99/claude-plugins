"""Hidden acceptance tests for task 07: distance tiers."""

import unittest
from decimal import Decimal

import freightlib
from freightlib import quotes, rates

D = Decimal


class RateTierTests(unittest.TestCase):
    def test_tier_boundaries_include_the_upper_limit(self) -> None:
        cases = [
            (0.01, 1),
            (1, 1),
            (100, 1),
            (100.01, 2),
            (101, 2),
            (500, 2),
            (500.01, 3),
            (501, 3),
            (10000, 3),
        ]
        for miles, tier in cases:
            with self.subTest(miles=miles):
                self.assertEqual(rates.rate_tier(miles), tier)

    def test_decimal_and_float_miles(self) -> None:
        self.assertEqual(rates.rate_tier(D("100.00")), 1)
        self.assertEqual(rates.rate_tier(D("100.001")), 2)
        self.assertEqual(rates.rate_tier(D("500.0")), 2)
        self.assertEqual(rates.rate_tier(D("500.5")), 3)
        self.assertEqual(rates.rate_tier(100.0), 1)
        self.assertEqual(rates.rate_tier(500.5), 3)

    def test_the_tier_is_an_int(self) -> None:
        self.assertIsInstance(rates.rate_tier(250), int)

    def test_invalid_miles_raise_the_calc_rate_message(self) -> None:
        for miles in (0, -1, float("nan"), D("-0.5")):
            with self.subTest(miles=miles):
                with self.assertRaises(ValueError) as caught:
                    rates.rate_tier(miles)
                self.assertEqual(str(caught.exception), "miles must be positive")


class TieredRateTests(unittest.TestCase):
    def test_standard_across_the_tiers(self) -> None:
        cases = [
            (100, "210.00"),
            (101, "190.89"),
            (500, "945.00"),
            (501, "841.68"),
            (1000, "1680.00"),
        ]
        for miles, expected in cases:
            with self.subTest(miles=miles):
                self.assertEqual(rates.calc_rate(miles, "standard"), D(expected))

    def test_bulk_and_expedited_across_the_tiers(self) -> None:
        cases = [
            (100, "bulk", "165.00"),
            (101, "bulk", "149.99"),
            (500, "bulk", "742.50"),
            (501, "bulk", "661.32"),
            (100, "expedited", "340.00"),
            (101, "expedited", "309.06"),
            (500, "expedited", "1530.00"),
            (501, "expedited", "1362.72"),
        ]
        for miles, service, expected in cases:
            with self.subTest(miles=miles, service=service):
                self.assertEqual(rates.calc_rate(miles, service), D(expected))

    def test_a_longer_shipment_can_cost_less_across_a_boundary(self) -> None:
        self.assertLess(rates.calc_rate(101, "standard"), rates.calc_rate(100, "standard"))
        self.assertLess(rates.calc_rate(501, "standard"), rates.calc_rate(500, "standard"))

    def test_the_discounted_rate_is_not_rounded_before_multiplying(self) -> None:
        # 101 x 1.485 = 149.985 rounds half up to 149.99. Rounding the rate to 1.49
        # first would give 150.49, and rounding half to even would give 149.98.
        self.assertEqual(rates.calc_rate(101, "bulk"), D("149.99"))

    def test_fractional_miles_use_the_tier_and_round_half_up(self) -> None:
        # 100.5 x 2.10 x 0.90 = 189.945
        self.assertEqual(rates.calc_rate(D("100.5"), "standard"), D("189.95"))
        self.assertEqual(rates.calc_rate(100.5, "standard"), D("189.95"))
        # 500.01 x 2.10 x 0.80 = 840.0168
        self.assertEqual(rates.calc_rate(D("500.01"), "standard"), D("840.02"))

    def test_short_hauls_still_pay_the_minimum(self) -> None:
        self.assertEqual(rates.calc_rate(10, "standard"), D("85.00"))
        self.assertEqual(rates.calc_rate(40, "bulk"), D("85.00"))

    def test_the_result_has_two_decimal_places(self) -> None:
        self.assertEqual(str(rates.calc_rate(500)), "945.00")
        self.assertEqual(str(rates.calc_rate(101, "bulk")), "149.99")

    def test_per_mile_rate_is_still_the_normal_rate(self) -> None:
        self.assertEqual(rates.per_mile_rate("standard"), D("2.10"))
        self.assertEqual(rates.per_mile_rate("bulk"), D("1.65"))
        self.assertEqual(rates.per_mile_rate("expedited"), D("3.40"))

    def test_round_trip_follows_the_tiers(self) -> None:
        # outbound 190.89, plus a return leg at 60%: 305.424
        self.assertEqual(rates.round_trip_rate(101, "standard"), D("305.42"))
        self.assertEqual(rates.round_trip_rate(100, "standard"), D("336.00"))

    def test_errors_are_unchanged(self) -> None:
        with self.assertRaisesRegex(ValueError, "^miles must be positive$"):
            rates.calc_rate(0)
        with self.assertRaisesRegex(ValueError, "^unknown service: air$"):
            rates.calc_rate(150, "air")


class QuoteTierTests(unittest.TestCase):
    def test_build_quote_records_the_tier(self) -> None:
        for miles, tier in ((100, 1), (101, 2), (500, 2), (501, 3)):
            with self.subTest(miles=miles):
                self.assertEqual(quotes.build_quote(miles, 20000).tier, tier)

    def test_the_line_haul_uses_the_tiered_rate(self) -> None:
        quote = quotes.build_quote(101, 20000, "standard", ["liftgate"])
        self.assertEqual(quote.lines[0].description, "Line haul (standard)")
        self.assertEqual(quote.lines[0].amount, D("190.89"))
        self.assertEqual(quote.total, D("225.89"))

    def test_the_tier_field_is_last_and_defaults_to_one(self) -> None:
        quote = quotes.Quote("standard", 10, 500, (), D("0.00"))
        self.assertEqual(quote.tier, 1)
        self.assertEqual(quotes.Quote("standard", 10, 500, (), D("0.00"), 3).tier, 3)

    def test_the_formatted_quote_is_unchanged(self) -> None:
        quote = quotes.build_quote(101, 20000, "standard", ["liftgate"])
        self.assertEqual(
            quotes.format_quote(quote).splitlines(),
            [
                "Line haul (standard)            190.89",
                "Liftgate                         35.00",
                "Total                           225.89",
            ],
        )


class ExportTests(unittest.TestCase):
    def test_rate_tier_is_exported(self) -> None:
        self.assertIs(freightlib.rate_tier, rates.rate_tier)
        self.assertIn("rate_tier", freightlib.__all__)


if __name__ == "__main__":
    unittest.main()
