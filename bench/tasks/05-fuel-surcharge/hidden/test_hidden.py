"""Hidden acceptance tests for task 05: the fuel surcharge."""

import unittest
from decimal import Decimal

import freightlib
from freightlib import quotes, rates

D = Decimal


class FuelSurchargeTests(unittest.TestCase):
    def test_rounds_half_up_to_the_cent(self) -> None:
        cases = [
            ("85.00", "12.5", "10.63"),
            ("85.00", "0.5", "0.43"),
            ("210.00", "8.25", "17.33"),
            ("100.00", "12.345", "12.35"),
            ("33.33", "7", "2.33"),
            ("33.33", "7.5", "2.50"),
            ("85.00", "12.4", "10.54"),
        ]
        for charge, percent, expected in cases:
            with self.subTest(charge=charge, percent=percent):
                self.assertEqual(rates.fuel_surcharge(D(charge), D(percent)), D(expected))

    def test_result_is_a_decimal_with_two_places(self) -> None:
        result = rates.fuel_surcharge(D("85.00"), D("12.5"))
        self.assertIsInstance(result, Decimal)
        self.assertEqual(str(result), "10.63")
        self.assertEqual(str(rates.fuel_surcharge(D("85.00"), D("0"))), "0.00")

    def test_zero_charge_is_allowed(self) -> None:
        self.assertEqual(rates.fuel_surcharge(D("0.00"), D("12.5")), D("0.00"))

    def test_percent_may_be_exactly_100_but_not_more(self) -> None:
        self.assertEqual(rates.fuel_surcharge(D("85.00"), D("100")), D("85.00"))
        with self.assertRaises(ValueError) as caught:
            rates.fuel_surcharge(D("85.00"), D("100.01"))
        self.assertEqual(str(caught.exception), "percent must not exceed 100")

    def test_negative_input_messages_and_their_order(self) -> None:
        with self.assertRaises(ValueError) as caught:
            rates.fuel_surcharge(D("-0.01"), D("5"))
        self.assertEqual(str(caught.exception), "charge must not be negative")
        with self.assertRaises(ValueError) as caught:
            rates.fuel_surcharge(D("85.00"), D("-0.5"))
        self.assertEqual(str(caught.exception), "percent must not be negative")
        with self.assertRaises(ValueError) as caught:
            rates.fuel_surcharge(D("-1"), D("-1"))
        self.assertEqual(str(caught.exception), "charge must not be negative")

    def test_is_exported_from_the_package(self) -> None:
        self.assertIs(freightlib.fuel_surcharge, rates.fuel_surcharge)
        self.assertIn("fuel_surcharge", freightlib.__all__)


class QuoteFuelLineTests(unittest.TestCase):
    def test_fuel_line_follows_the_line_haul_line(self) -> None:
        quote = quotes.build_quote(10, 500, "standard", fuel_percent=D("12.5"))
        self.assertEqual(
            quote.lines,
            (
                quotes.QuoteLine("Line haul (standard)", D("85.00")),
                quotes.QuoteLine("Fuel surcharge (12.5%)", D("10.63")),
            ),
        )
        self.assertEqual(quote.total, D("95.63"))

    def test_fuel_is_based_on_the_line_haul_only(self) -> None:
        quote = quotes.build_quote(
            100, 20000, "standard", ["liftgate", "hazmat"], fuel_percent=D("10")
        )
        self.assertEqual(
            [(line.description, line.amount) for line in quote.lines],
            [
                ("Line haul (standard)", D("210.00")),
                ("Fuel surcharge (10%)", D("21.00")),
                ("Liftgate", D("35.00")),
                ("Hazmat", D("75.00")),
            ],
        )
        self.assertEqual(quote.total, D("341.00"))

    def test_description_shows_the_percent_as_given(self) -> None:
        quote = quotes.build_quote(100, 20000, fuel_percent=D("12.50"))
        self.assertEqual(quote.lines[1].description, "Fuel surcharge (12.50%)")
        self.assertEqual(quote.lines[1].amount, D("26.25"))

    def test_basis_is_the_rounded_line_haul_amount(self) -> None:
        # The bulk rate for 100.5 miles is 165.825, shown as 165.83. Half of the
        # shown amount is 82.915, which rounds up to 82.92.
        quote = quotes.build_quote(D("100.5"), 20000, "bulk", fuel_percent=D("50"))
        self.assertEqual(quote.lines[0].amount, D("165.83"))
        self.assertEqual(quote.lines[1].amount, D("82.92"))
        self.assertEqual(quote.total, D("248.75"))

    def test_expedited_long_haul(self) -> None:
        quote = quotes.build_quote(100, 20000, "expedited", fuel_percent=D("9.5"))
        self.assertEqual(quote.lines[1].amount, D("32.30"))
        self.assertEqual(quote.total, D("372.30"))

    def test_zero_percent_adds_no_line(self) -> None:
        plain = quotes.build_quote(100, 20000)
        self.assertEqual(len(plain.lines), 1)
        self.assertEqual(plain.total, D("210.00"))
        for extra in ({}, {"fuel_percent": D("0")}, {"fuel_percent": D("0.00")}):
            with self.subTest(arguments=extra):
                quote = quotes.build_quote(100, 20000, **extra)
                self.assertEqual(quote, plain)

    def test_a_tiny_percent_still_adds_a_line(self) -> None:
        quote = quotes.build_quote(10, 500, fuel_percent=D("0.001"))
        self.assertEqual(len(quote.lines), 2)
        self.assertEqual(quote.lines[1].description, "Fuel surcharge (0.001%)")
        self.assertEqual(quote.lines[1].amount, D("0.00"))
        self.assertEqual(quote.total, D("85.00"))

    def test_invalid_percent_raises_the_same_messages(self) -> None:
        with self.assertRaises(ValueError) as caught:
            quotes.build_quote(100, 20000, fuel_percent=D("-1"))
        self.assertEqual(str(caught.exception), "percent must not be negative")
        with self.assertRaises(ValueError) as caught:
            quotes.build_quote(100, 20000, fuel_percent=D("101"))
        self.assertEqual(str(caught.exception), "percent must not exceed 100")

    def test_format_quote_shows_the_row(self) -> None:
        quote = quotes.build_quote(10, 500, fuel_percent=D("12.5"))
        rows = quotes.format_quote(quote).splitlines()
        self.assertEqual(len(rows), 3)
        self.assertTrue(rows[1].startswith("Fuel surcharge (12.5%)"))
        self.assertEqual(rows[1].split()[-1], "10.63")
        self.assertEqual(rows[2].split()[-1], "95.63")

    def test_quotes_without_fuel_are_unchanged(self) -> None:
        quote = quotes.build_quote(100, 20000, "standard", ["hazmat", "liftgate"])
        self.assertEqual(quote.total, D("320.00"))
        self.assertEqual([line.description for line in quote.lines], ["Line haul (standard)", "Hazmat", "Liftgate"])


if __name__ == "__main__":
    unittest.main()
