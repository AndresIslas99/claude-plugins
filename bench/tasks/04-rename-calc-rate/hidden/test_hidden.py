"""Hidden acceptance tests for task 04: rename calc_rate to job_rate."""

import os
import unittest
import warnings
from decimal import Decimal

import transferlib
from transferlib import quotes, rates


def deprecations(caught):
    return [w for w in caught if issubclass(w.category, DeprecationWarning)]


class JobRateTests(unittest.TestCase):
    def test_prices_like_the_old_function(self) -> None:
        cases = [
            ((100, "standard"), "210.00"),
            ((100, "bulk"), "165.00"),
            ((100, "priority"), "340.00"),
            ((10, "standard"), "85.00"),
            ((50,), "105.00"),
            ((Decimal("100.5"), "bulk"), "165.83"),
        ]
        for args, expected in cases:
            with self.subTest(args=args):
                self.assertEqual(rates.job_rate(*args), Decimal(expected))

    def test_keeps_the_defaults_and_keyword_names(self) -> None:
        self.assertEqual(rates.job_rate(100), Decimal("210.00"))
        self.assertEqual(rates.job_rate(gigabytes=100, service="bulk"), Decimal("165.00"))

    def test_raises_the_same_errors(self) -> None:
        with self.assertRaisesRegex(ValueError, "^gigabytes must be positive$"):
            rates.job_rate(0)
        with self.assertRaisesRegex(ValueError, "^unknown service: tape$"):
            rates.job_rate(100, "tape")

    def test_does_not_warn(self) -> None:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            rates.job_rate(100)
        self.assertEqual(caught, [])

    def test_is_exported_from_the_package(self) -> None:
        self.assertIs(transferlib.job_rate, rates.job_rate)
        self.assertIn("job_rate", transferlib.__all__)


class DeprecatedAliasTests(unittest.TestCase):
    def test_returns_what_the_new_function_returns(self) -> None:
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            self.assertEqual(rates.calc_rate(100, "bulk"), rates.job_rate(100, "bulk"))
            self.assertEqual(rates.calc_rate(100), Decimal("210.00"))
            self.assertEqual(rates.calc_rate(gigabytes=100, service="priority"), Decimal("340.00"))

    def test_emits_one_deprecation_warning_naming_the_new_function(self) -> None:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            rates.calc_rate(100)
        found = deprecations(caught)
        self.assertEqual(len(found), 1)
        self.assertIn("job_rate", str(found[0].message))

    def test_the_warning_points_at_the_calling_file(self) -> None:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            rates.calc_rate(100)
        found = deprecations(caught)
        self.assertEqual(len(found), 1)
        self.assertEqual(os.path.basename(found[0].filename), os.path.basename(__file__))

    def test_raises_the_same_errors(self) -> None:
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            with self.assertRaisesRegex(ValueError, "^gigabytes must be positive$"):
                rates.calc_rate(0)
            with self.assertRaisesRegex(ValueError, "^unknown service: tape$"):
                rates.calc_rate(100, "tape")

    def test_is_still_exported_from_the_package(self) -> None:
        self.assertIs(transferlib.calc_rate, rates.calc_rate)
        self.assertIn("calc_rate", transferlib.__all__)


class LibraryCallerTests(unittest.TestCase):
    def test_replicated_rate_does_not_use_the_deprecated_name(self) -> None:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            result = rates.replicated_rate(100, "standard")
        self.assertEqual(deprecations(caught), [])
        self.assertEqual(result, Decimal("336.00"))

    def test_build_quote_does_not_use_the_deprecated_name(self) -> None:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            quote = quotes.build_quote(100, 20000, "standard", ["encryption"])
        self.assertEqual(deprecations(caught), [])
        self.assertEqual(quote.total, Decimal("245.00"))

    def test_the_package_level_functions_do_not_warn_either(self) -> None:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            transferlib.replicated_rate(50)
            transferlib.build_quote(50, 1000)
        self.assertEqual(deprecations(caught), [])


if __name__ == "__main__":
    unittest.main()
