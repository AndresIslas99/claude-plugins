import unittest

from freightlib.validation import (
    MAX_WEIGHT_LB,
    validate_miles,
    validate_postal_code,
    validate_reference,
    validate_service,
    validate_weight_lb,
)


class ServiceTests(unittest.TestCase):
    def test_known_service_is_returned(self) -> None:
        self.assertEqual(validate_service("bulk"), "bulk")

    def test_unknown_service_raises(self) -> None:
        with self.assertRaisesRegex(ValueError, "unknown service: air"):
            validate_service("air")


class MilesTests(unittest.TestCase):
    def test_positive_miles_pass(self) -> None:
        self.assertEqual(validate_miles(12.5), 12.5)

    def test_zero_negative_and_nan_raise(self) -> None:
        for miles in (0, -1, float("nan")):
            with self.assertRaisesRegex(ValueError, "miles must be positive"):
                validate_miles(miles)


class WeightTests(unittest.TestCase):
    def test_weight_at_the_limit_passes(self) -> None:
        self.assertEqual(validate_weight_lb(MAX_WEIGHT_LB), MAX_WEIGHT_LB)

    def test_weight_must_be_positive(self) -> None:
        with self.assertRaisesRegex(ValueError, "weight must be positive"):
            validate_weight_lb(0)

    def test_weight_over_the_limit_raises(self) -> None:
        with self.assertRaisesRegex(ValueError, "weight must not exceed 45000 lb"):
            validate_weight_lb(45001)


class PostalCodeTests(unittest.TestCase):
    def test_surrounding_spaces_are_removed(self) -> None:
        self.assertEqual(validate_postal_code(" 75201 "), "75201")

    def test_wrong_length_and_letters_raise(self) -> None:
        for code in ("7520", "752011", "7520A", ""):
            with self.assertRaisesRegex(ValueError, "invalid postal code"):
                validate_postal_code(code)


class ReferenceTests(unittest.TestCase):
    def test_case_and_spaces_are_normalized(self) -> None:
        self.assertEqual(validate_reference(" fx123456 "), "FX123456")

    def test_bad_references_raise(self) -> None:
        for reference in ("FX12345", "F1234567", "123456FX", ""):
            with self.assertRaisesRegex(ValueError, "invalid reference"):
                validate_reference(reference)
