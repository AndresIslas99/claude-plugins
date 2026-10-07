import unittest
from decimal import Decimal

from transferlib.quotes import QuoteLine, build_quote, format_quote
from transferlib.rates import MINIMUM_CHARGE


class BuildQuoteTests(unittest.TestCase):
    def test_transfer_line_only(self) -> None:
        quote = build_quote(100, 20000)
        self.assertEqual(quote.lines, (QuoteLine("Transfer (standard)", Decimal("210.00")),))
        self.assertEqual(quote.total, Decimal("210.00"))

    def test_quote_records_its_inputs(self) -> None:
        quote = build_quote(100, 20000, "bulk")
        self.assertEqual((quote.service, quote.gigabytes, quote.size_gb), ("bulk", 100, 20000))

    def test_small_transfer_uses_the_minimum_charge(self) -> None:
        quote = build_quote(10, 500)
        self.assertEqual(quote.lines[0].amount, MINIMUM_CHARGE)
        self.assertEqual(quote.total, MINIMUM_CHARGE)

    def test_options_follow_in_the_order_given(self) -> None:
        quote = build_quote(100, 20000, "standard", ["compliance", "encryption"])
        self.assertEqual(
            [line.description for line in quote.lines],
            ["Transfer (standard)", "Compliance", "Encryption"],
        )
        self.assertEqual(quote.total, Decimal("320.00"))

    def test_unknown_option_raises(self) -> None:
        with self.assertRaisesRegex(ValueError, "unknown option: dedup"):
            build_quote(100, 20000, extras=["dedup"])

    def test_repeated_option_raises(self) -> None:
        with self.assertRaisesRegex(ValueError, "duplicate option: encryption"):
            build_quote(100, 20000, extras=["encryption", "encryption"])

    def test_inputs_are_validated(self) -> None:
        with self.assertRaisesRegex(ValueError, "size must be positive"):
            build_quote(100, 0)
        with self.assertRaisesRegex(ValueError, "gigabytes must be positive"):
            build_quote(0, 500)
        with self.assertRaisesRegex(ValueError, "unknown service: tape"):
            build_quote(100, 500, "tape")


class FormatQuoteTests(unittest.TestCase):
    def test_one_row_per_charge_and_a_total(self) -> None:
        quote = build_quote(100, 20000, "standard", ["encryption"])
        self.assertEqual(
            format_quote(quote).splitlines(),
            [
                "Transfer (standard)             210.00",
                "Encryption                       35.00",
                "Total                           245.00",
            ],
        )
