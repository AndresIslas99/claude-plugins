import unittest

from freightlib import units


class WeightTests(unittest.TestCase):
    def test_lb_to_kg(self) -> None:
        self.assertEqual(units.lb_to_kg(100), 45.3592)

    def test_kg_to_lb(self) -> None:
        self.assertEqual(units.kg_to_lb(10), 22.0462)

    def test_zero_is_allowed(self) -> None:
        self.assertEqual(units.lb_to_kg(0), 0.0)
        self.assertEqual(units.kg_to_lb(0), 0.0)

    def test_negative_weight_raises(self) -> None:
        with self.assertRaisesRegex(ValueError, "pounds must not be negative"):
            units.lb_to_kg(-1)
        with self.assertRaisesRegex(ValueError, "kilograms must not be negative"):
            units.kg_to_lb(-0.5)


class VolumeTests(unittest.TestCase):
    def test_cubic_feet_to_cubic_meters(self) -> None:
        self.assertEqual(units.cubic_feet_to_cubic_meters(100), 2.8317)

    def test_cubic_meters_to_cubic_feet(self) -> None:
        self.assertEqual(units.cubic_meters_to_cubic_feet(1), 35.3147)

    def test_negative_volume_raises(self) -> None:
        with self.assertRaisesRegex(ValueError, "cubic feet must not be negative"):
            units.cubic_feet_to_cubic_meters(-1)


class DimensionalWeightTests(unittest.TestCase):
    def test_default_divisor(self) -> None:
        self.assertEqual(units.dimensional_weight_lb(48, 40, 48), 663.0216)

    def test_custom_divisor(self) -> None:
        self.assertEqual(units.dimensional_weight_lb(10, 10, 10, divisor=166), 6.0241)

    def test_negative_side_raises(self) -> None:
        with self.assertRaisesRegex(ValueError, "width must not be negative"):
            units.dimensional_weight_lb(10, -1, 10)
