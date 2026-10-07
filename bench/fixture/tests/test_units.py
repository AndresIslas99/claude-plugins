import unittest

from transferlib import units


class GigabyteTests(unittest.TestCase):
    def test_gb_to_gib(self) -> None:
        self.assertEqual(units.gb_to_gib(100), 93.1323)

    def test_gib_to_gb(self) -> None:
        self.assertEqual(units.gib_to_gb(10), 10.7374)

    def test_zero_is_allowed(self) -> None:
        self.assertEqual(units.gb_to_gib(0), 0.0)
        self.assertEqual(units.gib_to_gb(0), 0.0)

    def test_negative_size_raises(self) -> None:
        with self.assertRaisesRegex(ValueError, "gigabytes must not be negative"):
            units.gb_to_gib(-1)
        with self.assertRaisesRegex(ValueError, "gibibytes must not be negative"):
            units.gib_to_gb(-0.5)


class TerabyteTests(unittest.TestCase):
    def test_tb_to_tib(self) -> None:
        self.assertEqual(units.tb_to_tib(100), 90.9495)

    def test_tib_to_tb(self) -> None:
        self.assertEqual(units.tib_to_tb(1), 1.0995)

    def test_negative_terabytes_raises(self) -> None:
        with self.assertRaisesRegex(ValueError, "terabytes must not be negative"):
            units.tb_to_tib(-1)


class BillableSizeTests(unittest.TestCase):
    def test_default_divisor(self) -> None:
        self.assertEqual(units.billable_size_gb(48, 40, 48), 663.0216)

    def test_custom_divisor(self) -> None:
        self.assertEqual(units.billable_size_gb(10, 10, 10, divisor=166), 6.0241)

    def test_negative_dimension_raises(self) -> None:
        with self.assertRaisesRegex(ValueError, "columns must not be negative"):
            units.billable_size_gb(10, -1, 10)
