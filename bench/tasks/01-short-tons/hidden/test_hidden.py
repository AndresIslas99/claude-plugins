"""Hidden acceptance tests for task 01: lb_to_short_tons."""

import unittest

import freightlib
from freightlib import units


def convert(pounds):
    # Looked up on every call so a missing function fails one test, not the whole module.
    return units.lb_to_short_tons(pounds)


class ShortTonsTests(unittest.TestCase):
    def test_exact_conversions(self) -> None:
        self.assertEqual(convert(2000), 1.0)
        self.assertEqual(convert(500), 0.25)
        self.assertEqual(convert(90000), 45.0)

    def test_zero_is_allowed(self) -> None:
        self.assertEqual(convert(0), 0.0)

    def test_result_is_rounded_to_four_places(self) -> None:
        self.assertEqual(convert(1234.5678), 0.6173)
        self.assertEqual(convert(12345), 6.1725)
        self.assertEqual(convert(1999), 0.9995)
        self.assertEqual(convert(1), 0.0005)
        self.assertEqual(convert(0.4), 0.0002)

    def test_result_is_a_float(self) -> None:
        self.assertIsInstance(convert(2000), float)
        self.assertIsInstance(convert(0), float)

    def test_negative_input_raises_with_the_exact_message(self) -> None:
        with self.assertRaises(ValueError) as caught:
            convert(-1)
        self.assertEqual(str(caught.exception), "pounds must not be negative")
        with self.assertRaises(ValueError):
            convert(-0.0001)

    def test_exported_from_the_package(self) -> None:
        self.assertIs(freightlib.lb_to_short_tons, units.lb_to_short_tons)
        self.assertIn("lb_to_short_tons", freightlib.__all__)

    def test_existing_conversions_are_unchanged(self) -> None:
        self.assertEqual(units.lb_to_kg(100), 45.3592)
        self.assertEqual(units.kg_to_lb(10), 22.0462)
        self.assertIn("lb_to_kg", freightlib.__all__)


if __name__ == "__main__":
    unittest.main()
