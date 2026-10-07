import unittest
from decimal import Decimal

from freightlib.quotes import QuoteLine, build_quote, format_quote
from freightlib.rates import MINIMUM_CHARGE


class BuildQuoteTests(unittest.TestCase):
    def test_line_haul_only(self) -> None:
        quote = build_quote(100, 20000)
        self.assertEqual(quote.lines, (QuoteLine("Line haul (standard)", Decimal("210.00")),))
        self.assertEqual(quote.total, Decimal("210.00"))

    def test_quote_records_its_inputs(self) -> None:
        quote = build_quote(100, 20000, "bulk")
        self.assertEqual((quote.service, quote.miles, quote.weight_lb), ("bulk", 100, 20000))

    def test_short_haul_uses_the_minimum_charge(self) -> None:
        quote = build_quote(10, 500)
        self.assertEqual(quote.lines[0].amount, MINIMUM_CHARGE)
        self.assertEqual(quote.total, MINIMUM_CHARGE)

    def test_surcharges_follow_in_the_order_given(self) -> None:
        quote = build_quote(100, 20000, "standard", ["hazmat", "liftgate"])
        self.assertEqual(
            [line.description for line in quote.lines],
            ["Line haul (standard)", "Hazmat", "Liftgate"],
        )
        self.assertEqual(quote.total, Decimal("320.00"))

    def test_unknown_surcharge_raises(self) -> None:
        with self.assertRaisesRegex(ValueError, "unknown surcharge: forklift"):
            build_quote(100, 20000, extras=["forklift"])

    def test_repeated_surcharge_raises(self) -> None:
        with self.assertRaisesRegex(ValueError, "duplicate surcharge: liftgate"):
            build_quote(100, 20000, extras=["liftgate", "liftgate"])

    def test_inputs_are_validated(self) -> None:
        with self.assertRaisesRegex(ValueError, "weight must be positive"):
            build_quote(100, 0)
        with self.assertRaisesRegex(ValueError, "miles must be positive"):
            build_quote(0, 500)
        with self.assertRaisesRegex(ValueError, "unknown service: air"):
            build_quote(100, 500, "air")


class FormatQuoteTests(unittest.TestCase):
    def test_one_row_per_charge_and_a_total(self) -> None:
        quote = build_quote(100, 20000, "standard", ["liftgate"])
        self.assertEqual(
            format_quote(quote).splitlines(),
            [
                "Line haul (standard)            210.00",
                "Liftgate                         35.00",
                "Total                           245.00",
            ],
        )
