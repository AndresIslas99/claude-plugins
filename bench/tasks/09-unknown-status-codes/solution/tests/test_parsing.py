import unittest
from datetime import datetime

from freightlib.parsing import StatusCode, StatusUpdate, parse_batch, parse_status

LINE = "FX123456|IT|2024-03-04 14:30|Dallas, TX|Left the origin yard"

KNOWN_CODES = {
    "PU": StatusCode.PICKED_UP,
    "IT": StatusCode.IN_TRANSIT,
    "OD": StatusCode.OUT_FOR_DELIVERY,
    "DL": StatusCode.DELIVERED,
    "EX": StatusCode.EXCEPTION,
}


class ParseStatusTests(unittest.TestCase):
    def test_parses_every_field(self) -> None:
        self.assertEqual(
            parse_status(LINE),
            StatusUpdate(
                reference="FX123456",
                status=StatusCode.IN_TRANSIT,
                timestamp=datetime(2024, 3, 4, 14, 30),
                location="Dallas, TX",
                note="Left the origin yard",
            ),
        )

    def test_note_is_optional(self) -> None:
        update = parse_status("FX123456|DL|2024-03-05 09:05|Austin, TX")
        self.assertEqual(update.status, StatusCode.DELIVERED)
        self.assertIsNone(update.note)

    def test_blank_note_becomes_none(self) -> None:
        update = parse_status("FX123456|DL|2024-03-05 09:05|Austin, TX|  ")
        self.assertIsNone(update.note)

    def test_fields_are_trimmed(self) -> None:
        update = parse_status("  fx123456 | PU | 2024-03-04 08:00 | Dallas, TX ")
        self.assertEqual(update.reference, "FX123456")
        self.assertEqual(update.location, "Dallas, TX")

    def test_every_known_code(self) -> None:
        for code, status in KNOWN_CODES.items():
            with self.subTest(code=code):
                update = parse_status(f"FX123456|{code}|2024-03-04 14:30|Dallas, TX")
                self.assertIs(update.status, status)

    def test_unknown_status_code_is_kept_as_unknown(self) -> None:
        update = parse_status("FX123456|ZZ|2024-03-04 14:30|Dallas, TX")
        self.assertIs(update.status, StatusCode.UNKNOWN)
        self.assertEqual(update.raw_code, "ZZ")

    def test_wrong_field_count_raises(self) -> None:
        with self.assertRaisesRegex(ValueError, "expected 4 or 5 fields, got 3"):
            parse_status("FX123456|IT|2024-03-04 14:30")

    def test_invalid_timestamp_raises(self) -> None:
        with self.assertRaisesRegex(ValueError, "invalid timestamp: 2024-13-04 14:30"):
            parse_status("FX123456|IT|2024-13-04 14:30|Dallas, TX")

    def test_missing_location_raises(self) -> None:
        with self.assertRaisesRegex(ValueError, "missing location"):
            parse_status("FX123456|IT|2024-03-04 14:30|")

    def test_invalid_reference_raises(self) -> None:
        with self.assertRaisesRegex(ValueError, "invalid reference"):
            parse_status("XX12|IT|2024-03-04 14:30|Dallas, TX")


class ParseBatchTests(unittest.TestCase):
    def test_parses_lines_and_skips_blanks(self) -> None:
        text = LINE + "\n\nFX654321|DL|2024-03-05 09:05|Austin, TX\n"
        updates = parse_batch(text)
        self.assertEqual([u.reference for u in updates], ["FX123456", "FX654321"])

    def test_empty_text_gives_no_updates(self) -> None:
        self.assertEqual(parse_batch(""), [])

    def test_error_names_the_line(self) -> None:
        text = LINE + "\nFX654321|DL|2024-03-05 09:05\n"
        with self.assertRaisesRegex(ValueError, "line 2: expected 4 or 5 fields, got 3"):
            parse_batch(text)
