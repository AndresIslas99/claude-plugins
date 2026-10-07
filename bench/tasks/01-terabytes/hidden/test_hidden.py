"""Hidden acceptance tests for task 01: gb_to_tb."""

import unittest

import transferlib
from transferlib import units


def convert(gigabytes):
    # Looked up on every call so a missing function fails one test, not the whole module.
    return units.gb_to_tb(gigabytes)


class GbToTbTests(unittest.TestCase):
    def test_exact_conversions(self) -> None:
        self.assertEqual(convert(1000), 1.0)
        self.assertEqual(convert(250), 0.25)
        self.assertEqual(convert(45000), 45.0)

    def test_zero_is_allowed(self) -> None:
        self.assertEqual(convert(0), 0.0)

    def test_result_is_rounded_to_four_places(self) -> None:
        self.assertEqual(convert(617.2839), 0.6173)
        self.assertEqual(convert(6172.5), 6.1725)
        self.assertEqual(convert(999.5), 0.9995)
        self.assertEqual(convert(0.5), 0.0005)
        self.assertEqual(convert(0.2), 0.0002)

    def test_result_is_a_float(self) -> None:
        self.assertIsInstance(convert(1000), float)
        self.assertIsInstance(convert(0), float)

    def test_negative_input_raises_with_the_exact_message(self) -> None:
        with self.assertRaises(ValueError) as caught:
            convert(-1)
        self.assertEqual(str(caught.exception), "gigabytes must not be negative")
        with self.assertRaises(ValueError):
            convert(-0.0001)

    def test_exported_from_the_package(self) -> None:
        self.assertIs(transferlib.gb_to_tb, units.gb_to_tb)
        self.assertIn("gb_to_tb", transferlib.__all__)

    def test_existing_conversions_are_unchanged(self) -> None:
        self.assertEqual(units.gb_to_gib(100), 93.1323)
        self.assertEqual(units.gib_to_gb(10), 10.7374)
        self.assertIn("gb_to_gib", transferlib.__all__)


if __name__ == "__main__":
    unittest.main()
