"""Hidden acceptance tests for task 03: validate_dimensions."""

import unittest

from freightlib import validation

NAN = float("nan")
INF = float("inf")


def problem(length, width, height):
    """Return the ValueError message for a box, or None when the box is accepted."""
    try:
        result = validation.validate_dimensions(length, width, height)
    except ValueError as error:
        return str(error)
    assert result is None, "validate_dimensions must return None"
    return None


class AcceptedBoxTests(unittest.TestCase):
    def test_a_normal_box_is_accepted(self) -> None:
        self.assertIsNone(problem(48, 40, 60))
        self.assertIsNone(problem(10.5, 0.25, 3))

    def test_the_limit_itself_is_allowed(self) -> None:
        self.assertIsNone(problem(636, 636, 636))

    def test_a_tiny_positive_side_is_allowed(self) -> None:
        self.assertIsNone(problem(0.01, 0.01, 0.01))


class PositiveCheckTests(unittest.TestCase):
    def test_each_side_must_be_positive(self) -> None:
        self.assertEqual(problem(0, 10, 10), "length must be positive")
        self.assertEqual(problem(10, -1, 10), "width must be positive")
        self.assertEqual(problem(10, 10, 0), "height must be positive")

    def test_nan_is_not_positive(self) -> None:
        self.assertEqual(problem(NAN, 10, 10), "length must be positive")
        self.assertEqual(problem(10, NAN, 10), "width must be positive")
        self.assertEqual(problem(10, 10, NAN), "height must be positive")

    def test_negative_infinity_is_not_positive(self) -> None:
        self.assertEqual(problem(10, 10, -INF), "height must be positive")


class LimitCheckTests(unittest.TestCase):
    def test_each_side_has_the_limit(self) -> None:
        self.assertEqual(problem(636.01, 10, 10), "length must not exceed 636 inches")
        self.assertEqual(problem(10, 637, 10), "width must not exceed 636 inches")
        self.assertEqual(problem(10, 10, 1000), "height must not exceed 636 inches")

    def test_infinity_is_over_the_limit(self) -> None:
        self.assertEqual(problem(10, INF, 10), "width must not exceed 636 inches")


class OrderOfChecksTests(unittest.TestCase):
    def test_the_first_problem_wins(self) -> None:
        self.assertEqual(problem(0, 0, 0), "length must be positive")
        self.assertEqual(problem(700, 0, 10), "length must not exceed 636 inches")
        self.assertEqual(problem(10, 0, 700), "width must be positive")
        self.assertEqual(problem(10, 700, 0), "width must not exceed 636 inches")
        self.assertEqual(problem(10, 10, 700), "height must not exceed 636 inches")


if __name__ == "__main__":
    unittest.main()
