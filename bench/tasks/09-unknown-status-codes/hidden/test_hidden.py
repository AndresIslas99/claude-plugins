"""Hidden acceptance tests for task 09: unknown status codes are not errors."""

import dataclasses
import unittest
from datetime import datetime

from freightlib import parsing
from freightlib.parsing import StatusCode, StatusUpdate

TAIL = "|2024-03-04 14:30|Dallas, TX"


def fx(code, tail=TAIL):
    return "FX123456|{}{}".format(code, tail)


class UnknownCodeTests(unittest.TestCase):
    def test_an_unknown_code_is_returned_not_raised(self) -> None:
        update = parsing.parse_status(fx("ZZ") + "|Held at the gate")
        self.assertIs(update.status, StatusCode.UNKNOWN)
        self.assertEqual(update.raw_code, "ZZ")
        self.assertEqual(update.reference, "FX123456")
        self.assertEqual(update.timestamp, datetime(2024, 3, 4, 14, 30))
        self.assertEqual(update.location, "Dallas, TX")
        self.assertEqual(update.note, "Held at the gate")

    def test_the_raw_code_is_the_trimmed_text_as_sent(self) -> None:
        self.assertEqual(parsing.parse_status("FX123456|  Zz9  |2024-03-04 14:30|Dallas, TX").raw_code, "Zz9")
        self.assertEqual(parsing.parse_status(fx("TOOLONG")).raw_code, "TOOLONG")

    def test_matching_is_exact_and_case_sensitive(self) -> None:
        for code in ("it", "Dl", "p u", "PUU", "I"):
            with self.subTest(code=code):
                update = parsing.parse_status(fx(code))
                self.assertIs(update.status, StatusCode.UNKNOWN)
                self.assertEqual(update.raw_code, code)

    def test_known_codes_have_no_raw_code(self) -> None:
        known = {
            "PU": StatusCode.PICKED_UP,
            "IT": StatusCode.IN_TRANSIT,
            "OD": StatusCode.OUT_FOR_DELIVERY,
            "DL": StatusCode.DELIVERED,
            "EX": StatusCode.EXCEPTION,
        }
        for code, status in known.items():
            with self.subTest(code=code):
                update = parsing.parse_status(fx(code))
                self.assertIs(update.status, status)
                self.assertIsNone(update.raw_code)

    def test_the_unknown_member_and_its_own_code(self) -> None:
        self.assertEqual(StatusCode.UNKNOWN.value, "??")
        update = parsing.parse_status(fx("??"))
        self.assertIs(update.status, StatusCode.UNKNOWN)
        self.assertEqual(update.raw_code, "??")

    def test_raw_code_is_the_last_field_and_defaults_to_none(self) -> None:
        fields = dataclasses.fields(StatusUpdate)
        self.assertEqual([f.name for f in fields], ["reference", "status", "timestamp", "location", "note", "raw_code"])
        self.assertIsNone(fields[-1].default)
        built = StatusUpdate("FX123456", StatusCode.DELIVERED, datetime(2024, 3, 5, 9, 5), "Austin, TX")
        self.assertIsNone(built.raw_code)
        self.assertEqual(parsing.parse_status("FX123456|DL|2024-03-05 09:05|Austin, TX"), built)


class ErrorsThatRemainTests(unittest.TestCase):
    def assertRejects(self, line, expected):
        with self.assertRaises(ValueError) as caught:
            parsing.parse_status(line)
        self.assertEqual(str(caught.exception), expected)

    def test_an_empty_status_field_is_still_an_error(self) -> None:
        self.assertRejects("FX123456||2024-03-04 14:30|Dallas, TX", "missing status code")
        self.assertRejects("FX123456|   |2024-03-04 14:30|Dallas, TX", "missing status code")

    def test_the_checks_keep_their_order(self) -> None:
        self.assertRejects("FX123456|ZZ|2024-03-04 14:30", "expected 4 or 5 fields, got 3")
        self.assertRejects("FX123456||2024-03-04 14:30", "expected 4 or 5 fields, got 3")
        self.assertRejects("FX123456||not-a-time|", "missing status code")
        self.assertRejects("FX123456|ZZ|not-a-time|", "invalid timestamp: not-a-time")
        self.assertRejects("FX123456|ZZ|2024-03-04 14:30|", "missing location")
        self.assertRejects("XX12|ZZ|2024-03-04 14:30|Dallas, TX", "invalid reference: 'XX12'")

    def test_the_other_messages_are_unchanged(self) -> None:
        self.assertRejects("FX123456|IT|2024-13-04 14:30|Dallas, TX", "invalid timestamp: 2024-13-04 14:30")
        self.assertRejects("FX123456|IT|2024-03-04 14:30|", "missing location")
        self.assertRejects("XX12|IT|2024-03-04 14:30|Dallas, TX", "invalid reference: 'XX12'")


class BatchTests(unittest.TestCase):
    def test_a_batch_keeps_lines_with_unknown_codes(self) -> None:
        text = "\n".join(
            [
                "FX111111|IT|2024-03-04 14:30|Dallas, TX",
                "FX222222|ZZ|2024-03-04 15:00|Waco, TX|Odd code",
                "",
                "FX333333|DL|2024-03-05 09:05|Austin, TX",
            ]
        )
        updates = parsing.parse_batch(text)
        self.assertEqual([u.reference for u in updates], ["FX111111", "FX222222", "FX333333"])
        self.assertEqual(
            [u.status for u in updates],
            [StatusCode.IN_TRANSIT, StatusCode.UNKNOWN, StatusCode.DELIVERED],
        )
        self.assertEqual([u.raw_code for u in updates], [None, "ZZ", None])

    def test_a_batch_still_reports_other_bad_lines_with_their_number(self) -> None:
        text = "FX111111|ZZ|2024-03-04 14:30|Dallas, TX\nFX222222|IT|2024-03-04 15:00\n"
        with self.assertRaises(ValueError) as caught:
            parsing.parse_batch(text)
        self.assertEqual(str(caught.exception), "line 2: expected 4 or 5 fields, got 3")

    def test_an_empty_status_in_a_batch_names_the_line(self) -> None:
        with self.assertRaises(ValueError) as caught:
            parsing.parse_batch("FX111111||2024-03-04 14:30|Dallas, TX")
        self.assertEqual(str(caught.exception), "line 1: missing status code")


if __name__ == "__main__":
    unittest.main()
