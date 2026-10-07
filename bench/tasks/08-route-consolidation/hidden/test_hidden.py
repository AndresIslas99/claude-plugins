"""Hidden acceptance tests for task 08: consolidating jobs by route."""

import dataclasses
import importlib
import unittest

import transferlib

NAN = float("nan")


def module():
    # Imported on every call so a missing module fails one test at a time.
    return importlib.import_module("transferlib.consolidation")


def job(job_id, size, source="us-east-1", target="eu-west-1"):
    return module().Job(job_id, source, target, size)


def consolidate(jobs, capacity):
    return module().consolidate(jobs, capacity)


def groups(batches):
    """The job ids on each batch, as a list of lists."""
    return [[item.job_id for item in batch.jobs] for batch in batches]


def routes(batches):
    return [(batch.source, batch.target) for batch in batches]


class DataTypeTests(unittest.TestCase):
    def test_job_is_a_frozen_dataclass_with_these_fields(self) -> None:
        item = job("A1", 1000)
        self.assertEqual(
            [f.name for f in dataclasses.fields(item)],
            ["job_id", "source", "target", "size_gb"],
        )
        self.assertEqual((item.job_id, item.source, item.target, item.size_gb), ("A1", "us-east-1", "eu-west-1", 1000))
        with self.assertRaises(dataclasses.FrozenInstanceError):
            item.size_gb = 5

    def test_batch_is_a_frozen_dataclass_with_a_total_size(self) -> None:
        first, second = job("A1", 1000), job("A2", 500.5)
        batch = module().Batch("US-EAST-1", "EU-WEST-1", (first, second))
        self.assertEqual([f.name for f in dataclasses.fields(batch)], ["source", "target", "jobs"])
        self.assertEqual(batch.total_size_gb, 1500.5)
        with self.assertRaises(dataclasses.FrozenInstanceError):
            batch.source = "US-WEST-2"

    def test_total_size_is_read_only(self) -> None:
        batch = module().Batch("US-EAST-1", "EU-WEST-1", (job("A1", 10),))
        with self.assertRaises(AttributeError):
            batch.total_size_gb = 99

    def test_jobs_are_returned_as_a_tuple_on_a_list_of_batches(self) -> None:
        first, second = job("A1", 400), job("A2", 500)
        result = consolidate([first, second], 1000)
        self.assertIsInstance(result, list)
        self.assertEqual(result, [module().Batch("US-EAST-1", "EU-WEST-1", (first, second))])
        self.assertEqual(result[0].jobs, (first, second))
        self.assertEqual(result[0].total_size_gb, 900)


class PackingRuleTests(unittest.TestCase):
    def test_jobs_are_packed_in_the_order_given(self) -> None:
        # Sorting biggest first would give [C, A] and [B] instead.
        jobs = [job("A", 4000), job("B", 5000), job("C", 6000)]
        self.assertEqual(groups(consolidate(jobs, 10000)), [["A", "B"], ["C"]])

    def test_a_job_goes_into_the_earliest_batch_with_room_not_the_tightest(self) -> None:
        # Best fit would put C on the second batch, which has exactly 3 left.
        jobs = [job("A", 5000), job("B", 7000), job("C", 3000)]
        self.assertEqual(groups(consolidate(jobs, 10000)), [["A", "C"], ["B"]])

    def test_a_later_job_can_go_back_to_an_earlier_batch(self) -> None:
        # Putting jobs only on the newest batch would give [A], [B, C].
        jobs = [job("A", 6000), job("B", 5000), job("C", 4000)]
        self.assertEqual(groups(consolidate(jobs, 10000)), [["A", "C"], ["B"]])

    def test_reaching_the_capacity_exactly_is_allowed(self) -> None:
        jobs = [job("A", 4000), job("B", 6000)]
        result = consolidate(jobs, 10000)
        self.assertEqual(groups(result), [["A", "B"]])
        self.assertEqual(result[0].total_size_gb, 10000)

    def test_a_job_of_exactly_the_capacity_gets_a_batch(self) -> None:
        self.assertEqual(groups(consolidate([job("A", 10000), job("B", 1)], 10000)), [["A"], ["B"]])

    def test_going_over_the_capacity_by_a_little_opens_a_new_batch(self) -> None:
        jobs = [job("A", 6000), job("B", 4000.5)]
        self.assertEqual(groups(consolidate(jobs, 10000)), [["A"], ["B"]])

    def test_a_longer_sequence_is_packed_by_the_rule(self) -> None:
        sizes = [60, 50, 40, 30, 20, 70, 10, 90]
        jobs = [job("L{}".format(i + 1), s) for i, s in enumerate(sizes)]
        expected = [["L1", "L3"], ["L2", "L4", "L5"], ["L6", "L7"], ["L8"]]
        self.assertEqual(groups(consolidate(jobs, 100)), expected)

    def test_jobs_keep_their_placement_order_inside_a_batch(self) -> None:
        jobs = [job("A", 3000), job("B", 4000), job("C", 2000)]
        self.assertEqual(groups(consolidate(jobs, 10000)), [["A", "B", "C"]])


class RouteTests(unittest.TestCase):
    def test_different_routes_never_share_a_batch(self) -> None:
        jobs = [job("A", 100, "us-east-1", "eu-west-1"), job("B", 100, "us-east-1", "us-west-1"), job("C", 100, "us-west-2", "eu-west-1")]
        result = consolidate(jobs, 10000)
        self.assertEqual(len(result), 3)
        self.assertEqual(routes(result), [("US-EAST-1", "EU-WEST-1"), ("US-EAST-1", "US-WEST-1"), ("US-WEST-2", "EU-WEST-1")])

    def test_the_reverse_route_is_a_different_route(self) -> None:
        jobs = [job("A", 100, "us-east-1", "eu-west-1"), job("B", 100, "eu-west-1", "us-east-1")]
        result = consolidate(jobs, 10000)
        self.assertEqual(routes(result), [("EU-WEST-1", "US-EAST-1"), ("US-EAST-1", "EU-WEST-1")])
        self.assertEqual(groups(result), [["B"], ["A"]])

    def test_names_ignore_case_and_surrounding_whitespace(self) -> None:
        jobs = [
            job("A", 100, " us-east-1 ", "eu-west-1"),
            job("B", 100, "US-EAST-1", "Eu-West-1  "),
            job("C", 100, "Us-East-1", "EU-WEST-1"),
        ]
        result = consolidate(jobs, 10000)
        self.assertEqual(groups(result), [["A", "B", "C"]])
        self.assertEqual(routes(result), [("US-EAST-1", "EU-WEST-1")])

    def test_batches_hold_the_normalized_names(self) -> None:
        result = consolidate([job("A", 100, "  east us", "west europe ")], 10000)
        self.assertEqual((result[0].source, result[0].target), ("EAST US", "WEST EUROPE"))

    def test_the_jobs_themselves_are_not_changed(self) -> None:
        original = job("A", 100, " us-east-1 ", "eu-west-1")
        result = consolidate([original], 10000)
        self.assertIs(result[0].jobs[0], original)
        self.assertEqual(original.source, " us-east-1 ")

    def test_the_result_is_sorted_by_route_then_by_opening_order(self) -> None:
        jobs = [
            job("L1", 600, "us-west-1", "eu-west-1"),
            job("L2", 600, "us-east-1", "us-west-2"),
            job("L3", 600, "us-east-1", "eu-west-1"),
            job("L4", 600, "us-east-1", "eu-west-1"),
            job("L5", 100, "us-east-1", "eu-west-1"),
        ]
        result = consolidate(jobs, 1000)
        self.assertEqual(routes(result), [
            ("US-EAST-1", "EU-WEST-1"),
            ("US-EAST-1", "EU-WEST-1"),
            ("US-EAST-1", "US-WEST-2"),
            ("US-WEST-1", "EU-WEST-1"),
        ])
        self.assertEqual(groups(result), [["L3", "L5"], ["L4"], ["L2"], ["L1"]])

    def test_each_route_is_packed_on_its_own(self) -> None:
        jobs = [
            job("A1", 6, "us-east-1", "eu-west-1"),
            job("B1", 6, "us-west-2", "eu-west-1"),
            job("A2", 5, "us-east-1", "eu-west-1"),
            job("B2", 4, "us-west-2", "eu-west-1"),
            job("A3", 4, "us-east-1", "eu-west-1"),
        ]
        self.assertEqual(groups(consolidate(jobs, 10)), [["A1", "A3"], ["A2"], ["B1", "B2"]])


class EdgeCaseTests(unittest.TestCase):
    def test_no_jobs_gives_an_empty_list(self) -> None:
        self.assertEqual(consolidate([], 1000), [])
        self.assertEqual(consolidate((), 1000), [])

    def test_a_tuple_of_jobs_is_accepted(self) -> None:
        jobs = (job("A", 400), job("B", 700))
        self.assertEqual(groups(consolidate(jobs, 1000)), [["A"], ["B"]])

    def test_the_input_sequence_is_not_modified(self) -> None:
        jobs = [job("A", 600), job("B", 700), job("C", 300)]
        snapshot = list(jobs)
        consolidate(jobs, 1000)
        self.assertEqual(jobs, snapshot)


class ValidationTests(unittest.TestCase):
    def assertRejects(self, jobs, capacity, expected):
        with self.assertRaises(ValueError) as caught:
            consolidate(jobs, capacity)
        self.assertEqual(str(caught.exception), expected)

    def test_capacity_must_be_positive(self) -> None:
        for capacity in (0, -1, -0.5, NAN):
            with self.subTest(capacity=capacity):
                self.assertRejects([job("A", 100)], capacity, "capacity must be positive")

    def test_capacity_is_checked_even_without_jobs(self) -> None:
        self.assertRejects([], 0, "capacity must be positive")

    def test_job_sizes_must_be_positive(self) -> None:
        for size in (0, -5, NAN):
            with self.subTest(size=size):
                self.assertRejects([job("A", 100), job("B2", size)], 1000, "size must be positive for job B2")

    def test_a_job_over_the_capacity_is_rejected(self) -> None:
        self.assertRejects([job("A", 100), job("C3", 1000.5)], 1000, "job C3 exceeds capacity")
        self.assertEqual(groups(consolidate([job("A", 1000)], 1000)), [["A"]])

    def test_the_capacity_is_checked_before_the_jobs(self) -> None:
        self.assertRejects([job("A", -1)], 0, "capacity must be positive")

    def test_the_first_bad_job_is_reported(self) -> None:
        self.assertRejects([job("A", 2000), job("B", 0)], 1000, "job A exceeds capacity")
        self.assertRejects([job("A", 0), job("B", 2000)], 1000, "size must be positive for job A")

    def test_nothing_is_returned_when_a_later_job_is_bad(self) -> None:
        self.assertRejects([job("A", 100), job("B", 200), job("C", -1)], 1000, "size must be positive for job C")


class ExportTests(unittest.TestCase):
    def test_the_names_are_exported_from_the_package(self) -> None:
        self.assertIs(transferlib.Job, module().Job)
        self.assertIs(transferlib.Batch, module().Batch)
        self.assertIs(transferlib.consolidate, module().consolidate)
        for name in ("Job", "Batch", "consolidate"):
            self.assertIn(name, transferlib.__all__)


if __name__ == "__main__":
    unittest.main()
