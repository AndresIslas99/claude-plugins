"""Hidden acceptance tests for task 08: consolidating loads by lane."""

import dataclasses
import importlib
import unittest

import freightlib

NAN = float("nan")


def module():
    # Imported on every call so a missing module fails one test at a time.
    return importlib.import_module("freightlib.consolidation")


def load(shipment_id, weight, origin="Dallas", destination="Austin"):
    return module().Load(shipment_id, origin, destination, weight)


def consolidate(loads, capacity):
    return module().consolidate(loads, capacity)


def groups(trucks):
    """The shipment ids on each truck, as a list of lists."""
    return [[item.shipment_id for item in truck.loads] for truck in trucks]


def lanes(trucks):
    return [(truck.origin, truck.destination) for truck in trucks]


class DataTypeTests(unittest.TestCase):
    def test_load_is_a_frozen_dataclass_with_these_fields(self) -> None:
        item = load("A1", 1000)
        self.assertEqual(
            [f.name for f in dataclasses.fields(item)],
            ["shipment_id", "origin", "destination", "weight_lb"],
        )
        self.assertEqual((item.shipment_id, item.origin, item.destination, item.weight_lb), ("A1", "Dallas", "Austin", 1000))
        with self.assertRaises(dataclasses.FrozenInstanceError):
            item.weight_lb = 5

    def test_truck_is_a_frozen_dataclass_with_a_total_weight(self) -> None:
        first, second = load("A1", 1000), load("A2", 500.5)
        truck = module().Truck("DALLAS", "AUSTIN", (first, second))
        self.assertEqual([f.name for f in dataclasses.fields(truck)], ["origin", "destination", "loads"])
        self.assertEqual(truck.total_weight_lb, 1500.5)
        with self.assertRaises(dataclasses.FrozenInstanceError):
            truck.origin = "WACO"

    def test_total_weight_is_read_only(self) -> None:
        truck = module().Truck("DALLAS", "AUSTIN", (load("A1", 10),))
        with self.assertRaises(AttributeError):
            truck.total_weight_lb = 99

    def test_loads_are_returned_as_a_tuple_on_a_list_of_trucks(self) -> None:
        first, second = load("A1", 400), load("A2", 500)
        result = consolidate([first, second], 1000)
        self.assertIsInstance(result, list)
        self.assertEqual(result, [module().Truck("DALLAS", "AUSTIN", (first, second))])
        self.assertEqual(result[0].loads, (first, second))
        self.assertEqual(result[0].total_weight_lb, 900)


class PackingRuleTests(unittest.TestCase):
    def test_loads_are_packed_in_the_order_given(self) -> None:
        # Sorting biggest first would give [C, A] and [B] instead.
        loads = [load("A", 4000), load("B", 5000), load("C", 6000)]
        self.assertEqual(groups(consolidate(loads, 10000)), [["A", "B"], ["C"]])

    def test_a_load_goes_on_the_earliest_truck_with_room_not_the_tightest(self) -> None:
        # Best fit would put C on the second truck, which has exactly 3 left.
        loads = [load("A", 5000), load("B", 7000), load("C", 3000)]
        self.assertEqual(groups(consolidate(loads, 10000)), [["A", "C"], ["B"]])

    def test_a_later_load_can_go_back_to_an_earlier_truck(self) -> None:
        # Putting loads only on the newest truck would give [A], [B, C].
        loads = [load("A", 6000), load("B", 5000), load("C", 4000)]
        self.assertEqual(groups(consolidate(loads, 10000)), [["A", "C"], ["B"]])

    def test_reaching_the_capacity_exactly_is_allowed(self) -> None:
        loads = [load("A", 4000), load("B", 6000)]
        result = consolidate(loads, 10000)
        self.assertEqual(groups(result), [["A", "B"]])
        self.assertEqual(result[0].total_weight_lb, 10000)

    def test_a_load_that_weighs_exactly_the_capacity_gets_a_truck(self) -> None:
        self.assertEqual(groups(consolidate([load("A", 10000), load("B", 1)], 10000)), [["A"], ["B"]])

    def test_going_over_the_capacity_by_a_little_opens_a_new_truck(self) -> None:
        loads = [load("A", 6000), load("B", 4000.5)]
        self.assertEqual(groups(consolidate(loads, 10000)), [["A"], ["B"]])

    def test_a_longer_sequence_is_packed_by_the_rule(self) -> None:
        weights = [60, 50, 40, 30, 20, 70, 10, 90]
        loads = [load("L{}".format(i + 1), w) for i, w in enumerate(weights)]
        expected = [["L1", "L3"], ["L2", "L4", "L5"], ["L6", "L7"], ["L8"]]
        self.assertEqual(groups(consolidate(loads, 100)), expected)

    def test_loads_keep_their_placement_order_inside_a_truck(self) -> None:
        loads = [load("A", 3000), load("B", 4000), load("C", 2000)]
        self.assertEqual(groups(consolidate(loads, 10000)), [["A", "B", "C"]])


class LaneTests(unittest.TestCase):
    def test_different_lanes_never_share_a_truck(self) -> None:
        loads = [load("A", 100, "Dallas", "Austin"), load("B", 100, "Dallas", "Houston"), load("C", 100, "Waco", "Austin")]
        result = consolidate(loads, 10000)
        self.assertEqual(len(result), 3)
        self.assertEqual(lanes(result), [("DALLAS", "AUSTIN"), ("DALLAS", "HOUSTON"), ("WACO", "AUSTIN")])

    def test_the_reverse_lane_is_a_different_lane(self) -> None:
        loads = [load("A", 100, "Dallas", "Austin"), load("B", 100, "Austin", "Dallas")]
        result = consolidate(loads, 10000)
        self.assertEqual(lanes(result), [("AUSTIN", "DALLAS"), ("DALLAS", "AUSTIN")])
        self.assertEqual(groups(result), [["B"], ["A"]])

    def test_names_ignore_case_and_surrounding_whitespace(self) -> None:
        loads = [
            load("A", 100, " dallas ", "austin"),
            load("B", 100, "DALLAS", "Austin  "),
            load("C", 100, "Dallas", "AUSTIN"),
        ]
        result = consolidate(loads, 10000)
        self.assertEqual(groups(result), [["A", "B", "C"]])
        self.assertEqual(lanes(result), [("DALLAS", "AUSTIN")])

    def test_trucks_hold_the_normalized_names(self) -> None:
        result = consolidate([load("A", 100, "  fort worth", "el paso ")], 10000)
        self.assertEqual((result[0].origin, result[0].destination), ("FORT WORTH", "EL PASO"))

    def test_the_loads_themselves_are_not_changed(self) -> None:
        original = load("A", 100, " dallas ", "austin")
        result = consolidate([original], 10000)
        self.assertIs(result[0].loads[0], original)
        self.assertEqual(original.origin, " dallas ")

    def test_the_result_is_sorted_by_lane_then_by_opening_order(self) -> None:
        loads = [
            load("L1", 600, "Houston", "Austin"),
            load("L2", 600, "Dallas", "Waco"),
            load("L3", 600, "Dallas", "Austin"),
            load("L4", 600, "dallas", "austin"),
            load("L5", 100, "Dallas", "Austin"),
        ]
        result = consolidate(loads, 1000)
        self.assertEqual(lanes(result), [
            ("DALLAS", "AUSTIN"),
            ("DALLAS", "AUSTIN"),
            ("DALLAS", "WACO"),
            ("HOUSTON", "AUSTIN"),
        ])
        self.assertEqual(groups(result), [["L3", "L5"], ["L4"], ["L2"], ["L1"]])

    def test_each_lane_is_packed_on_its_own(self) -> None:
        loads = [
            load("A1", 6, "Dallas", "Austin"),
            load("B1", 6, "Waco", "Austin"),
            load("A2", 5, "Dallas", "Austin"),
            load("B2", 4, "Waco", "Austin"),
            load("A3", 4, "Dallas", "Austin"),
        ]
        self.assertEqual(groups(consolidate(loads, 10)), [["A1", "A3"], ["A2"], ["B1", "B2"]])


class EdgeCaseTests(unittest.TestCase):
    def test_no_loads_gives_an_empty_list(self) -> None:
        self.assertEqual(consolidate([], 1000), [])
        self.assertEqual(consolidate((), 1000), [])

    def test_a_tuple_of_loads_is_accepted(self) -> None:
        loads = (load("A", 400), load("B", 700))
        self.assertEqual(groups(consolidate(loads, 1000)), [["A"], ["B"]])

    def test_the_input_sequence_is_not_modified(self) -> None:
        loads = [load("A", 600), load("B", 700), load("C", 300)]
        snapshot = list(loads)
        consolidate(loads, 1000)
        self.assertEqual(loads, snapshot)


class ValidationTests(unittest.TestCase):
    def assertRejects(self, loads, capacity, expected):
        with self.assertRaises(ValueError) as caught:
            consolidate(loads, capacity)
        self.assertEqual(str(caught.exception), expected)

    def test_capacity_must_be_positive(self) -> None:
        for capacity in (0, -1, -0.5, NAN):
            with self.subTest(capacity=capacity):
                self.assertRejects([load("A", 100)], capacity, "capacity must be positive")

    def test_capacity_is_checked_even_without_loads(self) -> None:
        self.assertRejects([], 0, "capacity must be positive")

    def test_load_weights_must_be_positive(self) -> None:
        for weight in (0, -5, NAN):
            with self.subTest(weight=weight):
                self.assertRejects([load("A", 100), load("B2", weight)], 1000, "weight must be positive for load B2")

    def test_a_load_over_the_capacity_is_rejected(self) -> None:
        self.assertRejects([load("A", 100), load("C3", 1000.5)], 1000, "load C3 exceeds capacity")
        self.assertEqual(groups(consolidate([load("A", 1000)], 1000)), [["A"]])

    def test_the_capacity_is_checked_before_the_loads(self) -> None:
        self.assertRejects([load("A", -1)], 0, "capacity must be positive")

    def test_the_first_bad_load_is_reported(self) -> None:
        self.assertRejects([load("A", 2000), load("B", 0)], 1000, "load A exceeds capacity")
        self.assertRejects([load("A", 0), load("B", 2000)], 1000, "weight must be positive for load A")

    def test_nothing_is_returned_when_a_later_load_is_bad(self) -> None:
        self.assertRejects([load("A", 100), load("B", 200), load("C", -1)], 1000, "weight must be positive for load C")


class ExportTests(unittest.TestCase):
    def test_the_names_are_exported_from_the_package(self) -> None:
        self.assertIs(freightlib.Load, module().Load)
        self.assertIs(freightlib.Truck, module().Truck)
        self.assertIs(freightlib.consolidate, module().consolidate)
        for name in ("Load", "Truck", "consolidate"):
            self.assertIn(name, freightlib.__all__)


if __name__ == "__main__":
    unittest.main()
