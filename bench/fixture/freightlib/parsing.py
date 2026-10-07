"""Parsing carrier status messages into dataclasses.

Carrier FX sends one message per line. The fields are separated by ``|``::

    FX123456|IT|2024-03-04 14:30|Dallas, TX|Left the origin yard

The last field, the note, is optional.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import List, Optional

from freightlib.validation import validate_reference

TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M"


class StatusCode(Enum):
    """The shipment states that carriers report."""

    PICKED_UP = "PU"
    IN_TRANSIT = "IT"
    OUT_FOR_DELIVERY = "OD"
    DELIVERED = "DL"
    EXCEPTION = "EX"


@dataclass(frozen=True)
class StatusUpdate:
    """One status event for a shipment."""

    reference: str
    status: StatusCode
    timestamp: datetime
    location: str
    note: Optional[str] = None


def parse_status(line: str) -> StatusUpdate:
    """Parse one carrier FX message into a ``StatusUpdate``.

    Raises ``ValueError`` when the message is malformed.
    """
    fields = [field.strip() for field in line.split("|")]
    if len(fields) not in (4, 5):
        raise ValueError(f"expected 4 or 5 fields, got {len(fields)}")
    reference, code, stamp, location = fields[:4]
    note = fields[4] if len(fields) == 5 and fields[4] else None
    try:
        status = StatusCode(code)
    except ValueError:
        raise ValueError(f"unknown status code: {code}") from None
    try:
        timestamp = datetime.strptime(stamp, TIMESTAMP_FORMAT)
    except ValueError:
        raise ValueError(f"invalid timestamp: {stamp}") from None
    if not location:
        raise ValueError("missing location")
    return StatusUpdate(validate_reference(reference), status, timestamp, location, note)


def parse_batch(text: str) -> List[StatusUpdate]:
    """Parse a block of messages, one per line. Blank lines are skipped.

    A bad line raises ``ValueError`` whose message starts with the line number,
    for example ``line 3: missing location``.
    """
    updates: List[StatusUpdate] = []
    for number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            updates.append(parse_status(line))
        except ValueError as error:
            raise ValueError(f"line {number}: {error}") from None
    return updates
