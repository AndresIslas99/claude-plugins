"""Hidden acceptance tests for task 06: the Northline message format."""

import unittest
from datetime import datetime

import transferlib
from transferlib import parsing
from transferlib.parsing import StatusCode, StatusUpdate

FX_LINE = "FX123456|IT|2024-03-04 14:30|us-east-1, az-a|Left the source queue"


def message(**overrides):
    """Build a Northline message. A value of None leaves the key out."""
    fields = {
        "ref": "NL-778899",
        "status": "in_transfer",
        "time": "2024-03-04T14:30:00-06:00",
        "region": "us-east-1",
        "zone": "az-a",
        "note": "Left the queue",
    }
    fields.update(overrides)
    return ";".join("{}={}".format(key, value) for key, value in fields.items() if value is not None)


class NorthlineCase(unittest.TestCase):
    def assertRejects(self, text, expected, parse=None):
        # The parser is looked up here so a missing function fails one test at a time.
        parse = parse or parsing.parse_northline
        with self.assertRaises(ValueError) as caught:
            parse(text)
        self.assertEqual(str(caught.exception), expected)


class NorthlineFieldTests(NorthlineCase):
    def test_parses_a_full_message(self) -> None:
        self.assertEqual(
            parsing.parse_northline(message()),
            StatusUpdate(
                reference="NL-778899",
                status=StatusCode.IN_TRANSFER,
                timestamp=datetime(2024, 3, 4, 20, 30),
                location="us-east-1, az-a",
                note="Left the queue",
            ),
        )

    def test_every_status_name_in_any_letter_case(self) -> None:
        cases = {
            "pulled": StatusCode.PULLED,
            "IN_TRANSFER": StatusCode.IN_TRANSFER,
            "On_Disk": StatusCode.ON_DISK,
            "delivered": StatusCode.DELIVERED,
            "EXCEPTION": StatusCode.EXCEPTION,
        }
        for name, status in cases.items():
            with self.subTest(status=name):
                self.assertIs(parsing.parse_northline(message(status=name)).status, status)

    def test_reference_is_upper_cased(self) -> None:
        self.assertEqual(parsing.parse_northline(message(ref="nl-778899")).reference, "NL-778899")
        self.assertEqual(parsing.parse_northline(message(ref="  Nl-000123  ")).reference, "NL-000123")

    def test_location_with_and_without_a_zone(self) -> None:
        self.assertEqual(parsing.parse_northline(message()).location, "us-east-1, az-a")
        self.assertEqual(parsing.parse_northline(message(zone=None)).location, "us-east-1")
        self.assertEqual(parsing.parse_northline(message(zone="  ")).location, "us-east-1")
        self.assertEqual(parsing.parse_northline(message(zone="")).location, "us-east-1")

    def test_the_note_is_optional_and_blank_becomes_none(self) -> None:
        self.assertIsNone(parsing.parse_northline(message(note=None)).note)
        self.assertIsNone(parsing.parse_northline(message(note="")).note)
        self.assertIsNone(parsing.parse_northline(message(note="   ")).note)

    def test_a_note_may_contain_equals_signs(self) -> None:
        update = parsing.parse_northline(message(note="shard=4, node=b=7"))
        self.assertEqual(update.note, "shard=4, node=b=7")

    def test_keys_are_case_insensitive_and_in_any_order(self) -> None:
        text = "REGION=eu-west-1;Time=2024-03-05T09:05:00Z;STATUS=Delivered;Ref=NL-000042"
        self.assertEqual(
            parsing.parse_northline(text),
            StatusUpdate("NL-000042", StatusCode.DELIVERED, datetime(2024, 3, 5, 9, 5), "eu-west-1", None),
        )

    def test_whitespace_is_trimmed_and_empty_pieces_are_ignored(self) -> None:
        text = "  ref = NL-778899 ; status= delivered ;; time=2024-03-04T14:30:00Z; region = eu-west-1 ; ;"
        update = parsing.parse_northline(text)
        self.assertEqual(update.reference, "NL-778899")
        self.assertEqual(update.status, StatusCode.DELIVERED)
        self.assertEqual(update.location, "eu-west-1")

    def test_other_keys_are_ignored(self) -> None:
        self.assertEqual(
            parsing.parse_northline(message(worker="Sam", queue="7")),
            parsing.parse_northline(message()),
        )


class NorthlineTimeTests(NorthlineCase):
    def test_offsets_are_applied_to_give_utc(self) -> None:
        cases = [
            ("2024-03-04T14:30:00Z", datetime(2024, 3, 4, 14, 30)),
            ("2024-03-04T14:30:00", datetime(2024, 3, 4, 14, 30)),
            ("2024-03-04T14:30:00+00:00", datetime(2024, 3, 4, 14, 30)),
            ("2024-03-04T14:30:00-06:00", datetime(2024, 3, 4, 20, 30)),
            ("2024-03-04T14:30:15+05:30", datetime(2024, 3, 4, 9, 0, 15)),
            ("2023-12-31T23:30:00-02:00", datetime(2024, 1, 1, 1, 30)),
            ("2024-03-01T00:30:00+01:00", datetime(2024, 2, 29, 23, 30)),
        ]
        for text, expected in cases:
            with self.subTest(time=text):
                self.assertEqual(parsing.parse_northline(message(time=text)).timestamp, expected)

    def test_the_result_has_no_tzinfo(self) -> None:
        for text in ("2024-03-04T14:30:00Z", "2024-03-04T14:30:00-06:00", "2024-03-04T14:30:00"):
            with self.subTest(time=text):
                self.assertIsNone(parsing.parse_northline(message(time=text)).timestamp.tzinfo)

    def test_values_that_are_not_real_times_are_rejected(self) -> None:
        for text in ("not-a-time", "2024-13-45T00:00:00Z", "2024-03-04T25:00:00Z", "2024-02-30T10:00:00Z"):
            with self.subTest(time=text):
                self.assertRejects(message(time=text), "invalid time: " + text)

    def test_the_time_must_have_the_stated_shape(self) -> None:
        shapes = [
            "2024-03-04",
            "2024-03-04T14:30",
            "2024-03-04T14:30:00.5Z",
            "2024-03-04 14:30:00Z",
            "2024-03-04T14:30:00+0100",
        ]
        for text in shapes:
            with self.subTest(time=text):
                self.assertRejects(message(time=text), "invalid time: " + text)

    def test_the_invalid_time_message_uses_the_trimmed_value(self) -> None:
        self.assertRejects(message(time="  yesterday  "), "invalid time: yesterday")


class NorthlineErrorTests(NorthlineCase):
    def test_malformed_pairs(self) -> None:
        self.assertRejects("ref=NL-778899;oops", "malformed pair: oops")
        self.assertRejects("ref=NL-778899;   oops   ", "malformed pair: oops")
        self.assertRejects(message() + ";=orphan", "malformed pair: =orphan")

    def test_duplicate_keys(self) -> None:
        self.assertRejects("ref=NL-778899;REF=NL-000001", "duplicate key: ref")
        self.assertRejects(message() + ";foo=1;FOO=2", "duplicate key: foo")
        self.assertRejects(message() + ";note=again", "duplicate key: note")

    def test_missing_fields_are_reported_in_order(self) -> None:
        self.assertRejects("", "missing field: ref")
        self.assertRejects(" ; ; ", "missing field: ref")
        self.assertRejects(message(ref=None, status=None), "missing field: ref")
        self.assertRejects(message(status=None, time=None), "missing field: status")
        self.assertRejects(message(time=None, region=None), "missing field: time")
        self.assertRejects(message(region=None), "missing field: region")

    def test_blank_values_count_as_missing(self) -> None:
        self.assertRejects(message(status=""), "missing field: status")
        self.assertRejects(message(region="   "), "missing field: region")
        self.assertRejects(message(ref=""), "missing field: ref")

    def test_invalid_references(self) -> None:
        for value in ("NL-12345", "NL-1234567", "XX-778899", "NL778899", "NL-77889A", "nl-12"):
            with self.subTest(ref=value):
                self.assertRejects(message(ref=value), "invalid reference: " + value)

    def test_unknown_statuses(self) -> None:
        for value in ("lost", "In Transfer", "delivered!", "PU"):
            with self.subTest(status=value):
                self.assertRejects(message(status=value), "unknown status: " + value)

    def test_the_first_problem_is_the_one_reported(self) -> None:
        self.assertRejects(message(region=None, status="lost"), "missing field: region")
        self.assertRejects(message(ref="bad", status="lost", time="bad"), "invalid reference: bad")
        self.assertRejects(message(status="lost", time="bad"), "unknown status: lost")
        self.assertRejects("oops;ref=NL-778899", "malformed pair: oops")
        self.assertRejects("a=1;a=2;oops", "duplicate key: a")
        self.assertRejects("oops;a=1;a=2", "malformed pair: oops")


class ParseMessageTests(NorthlineCase):
    def test_each_format_goes_to_its_own_parser(self) -> None:
        self.assertEqual(parsing.parse_message(FX_LINE), parsing.parse_status(FX_LINE))
        self.assertEqual(parsing.parse_message(message()), parsing.parse_northline(message()))

    def test_leading_whitespace_and_letter_case_of_ref(self) -> None:
        text = "   REF=NL-778899;status=delivered;time=2024-03-04T14:30:00Z;region=eu-west-1"
        update = parsing.parse_message(text)
        self.assertEqual(update.reference, "NL-778899")
        self.assertEqual(update.location, "eu-west-1")

    def test_a_northline_message_must_start_with_ref(self) -> None:
        text = "status=delivered;ref=NL-778899;time=2024-03-04T14:30:00Z;region=eu-west-1"
        self.assertRejects(text, "expected 4 or 5 fields, got 1", parse=parsing.parse_message)

    def test_errors_come_from_the_matching_parser(self) -> None:
        self.assertRejects("FX123456|ZZ|2024-03-04 14:30|us-east-1, az-a", "unknown status code: ZZ", parse=parsing.parse_message)
        self.assertRejects(message(region=None), "missing field: region", parse=parsing.parse_message)


class ParseBatchTests(NorthlineCase):
    def test_a_batch_may_mix_both_formats(self) -> None:
        text = FX_LINE + "\r\n\r\n" + message(status="delivered") + "\n  \n" + "FX654321|DL|2024-03-05 09:05|eu-west-1, az-b\n"
        updates = parsing.parse_batch(text)
        self.assertEqual([u.reference for u in updates], ["FX123456", "NL-778899", "FX654321"])
        self.assertEqual(updates[1].status, StatusCode.DELIVERED)

    def test_northline_errors_get_the_line_prefix(self) -> None:
        text = FX_LINE + "\n" + message(region=None) + "\n"
        self.assertRejects(text, "line 2: missing field: region", parse=parsing.parse_batch)

    def test_fx_errors_keep_their_line_prefix(self) -> None:
        text = message() + "\n\nFX654321|DL|2024-03-05 09:05\n"
        self.assertRejects(text, "line 3: expected 4 or 5 fields, got 3", parse=parsing.parse_batch)

    def test_an_empty_batch(self) -> None:
        self.assertEqual(parsing.parse_batch(""), [])
        self.assertEqual(parsing.parse_batch("\n \n"), [])


class ExportTests(unittest.TestCase):
    def test_new_functions_are_exported(self) -> None:
        self.assertIs(transferlib.parse_northline, parsing.parse_northline)
        self.assertIs(transferlib.parse_message, parsing.parse_message)
        self.assertIn("parse_northline", transferlib.__all__)
        self.assertIn("parse_message", transferlib.__all__)


if __name__ == "__main__":
    unittest.main()
