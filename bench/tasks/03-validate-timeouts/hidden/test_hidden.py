"""Hidden acceptance tests for task 03: validate_timeouts."""

import unittest

from transferlib import validation

NAN = float("nan")
INF = float("inf")


def problem(connect, read, total):
    """Return the ValueError message for a set of timeouts, or None when they are accepted."""
    try:
        result = validation.validate_timeouts(connect, read, total)
    except ValueError as error:
        return str(error)
    assert result is None, "validate_timeouts must return None"
    return None


class AcceptedTimeoutsTests(unittest.TestCase):
    def test_normal_timeouts_are_accepted(self) -> None:
        self.assertIsNone(problem(48, 40, 60))
        self.assertIsNone(problem(10.5, 0.25, 3))

    def test_the_limit_itself_is_allowed(self) -> None:
        self.assertIsNone(problem(636, 636, 636))

    def test_a_tiny_positive_timeout_is_allowed(self) -> None:
        self.assertIsNone(problem(0.01, 0.01, 0.01))


class PositiveCheckTests(unittest.TestCase):
    def test_each_timeout_must_be_positive(self) -> None:
        self.assertEqual(problem(0, 10, 10), "connect must be positive")
        self.assertEqual(problem(10, -1, 10), "read must be positive")
        self.assertEqual(problem(10, 10, 0), "total must be positive")

    def test_nan_is_not_positive(self) -> None:
        self.assertEqual(problem(NAN, 10, 10), "connect must be positive")
        self.assertEqual(problem(10, NAN, 10), "read must be positive")
        self.assertEqual(problem(10, 10, NAN), "total must be positive")

    def test_negative_infinity_is_not_positive(self) -> None:
        self.assertEqual(problem(10, 10, -INF), "total must be positive")


class LimitCheckTests(unittest.TestCase):
    def test_each_timeout_has_the_limit(self) -> None:
        self.assertEqual(problem(636.01, 10, 10), "connect must not exceed 636 seconds")
        self.assertEqual(problem(10, 637, 10), "read must not exceed 636 seconds")
        self.assertEqual(problem(10, 10, 1000), "total must not exceed 636 seconds")

    def test_infinity_is_over_the_limit(self) -> None:
        self.assertEqual(problem(10, INF, 10), "read must not exceed 636 seconds")


class OrderOfChecksTests(unittest.TestCase):
    def test_the_first_problem_wins(self) -> None:
        self.assertEqual(problem(0, 0, 0), "connect must be positive")
        self.assertEqual(problem(700, 0, 10), "connect must not exceed 636 seconds")
        self.assertEqual(problem(10, 0, 700), "read must be positive")
        self.assertEqual(problem(10, 700, 0), "read must not exceed 636 seconds")
        self.assertEqual(problem(10, 10, 700), "total must not exceed 636 seconds")


if __name__ == "__main__":
    unittest.main()
