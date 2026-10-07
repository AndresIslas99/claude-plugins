import unittest

from transferlib.validation import (
    MAX_SIZE_GB,
    validate_account_number,
    validate_gigabytes,
    validate_reference,
    validate_service,
    validate_size_gb,
)


class ServiceTests(unittest.TestCase):
    def test_known_service_is_returned(self) -> None:
        self.assertEqual(validate_service("bulk"), "bulk")

    def test_unknown_service_raises(self) -> None:
        with self.assertRaisesRegex(ValueError, "unknown service: tape"):
            validate_service("tape")


class GigabytesTests(unittest.TestCase):
    def test_positive_gigabytes_pass(self) -> None:
        self.assertEqual(validate_gigabytes(12.5), 12.5)

    def test_zero_negative_and_nan_raise(self) -> None:
        for gigabytes in (0, -1, float("nan")):
            with self.assertRaisesRegex(ValueError, "gigabytes must be positive"):
                validate_gigabytes(gigabytes)


class SizeTests(unittest.TestCase):
    def test_size_at_the_limit_passes(self) -> None:
        self.assertEqual(validate_size_gb(MAX_SIZE_GB), MAX_SIZE_GB)

    def test_size_must_be_positive(self) -> None:
        with self.assertRaisesRegex(ValueError, "size must be positive"):
            validate_size_gb(0)

    def test_size_over_the_limit_raises(self) -> None:
        with self.assertRaisesRegex(ValueError, "size must not exceed 45000 GB"):
            validate_size_gb(45001)


class AccountNumberTests(unittest.TestCase):
    def test_surrounding_spaces_are_removed(self) -> None:
        self.assertEqual(validate_account_number(" 42017 "), "42017")

    def test_wrong_length_and_letters_raise(self) -> None:
        for code in ("4201", "420171", "4201A", ""):
            with self.assertRaisesRegex(ValueError, "invalid account number"):
                validate_account_number(code)


class ReferenceTests(unittest.TestCase):
    def test_case_and_spaces_are_normalized(self) -> None:
        self.assertEqual(validate_reference(" fx123456 "), "FX123456")

    def test_bad_references_raise(self) -> None:
        for reference in ("FX12345", "F1234567", "123456FX", ""):
            with self.assertRaisesRegex(ValueError, "invalid reference"):
                validate_reference(reference)
