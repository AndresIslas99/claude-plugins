"""Parsing carrier status messages into dataclasses.

Carrier FX sends one message per line. The fields are separated by ``|``::

    FX123456|IT|2024-03-04 14:30|Dallas, TX|Left the origin yard

The last field, the note, is optional.

Carrier Northline sends ``key=value`` pairs separated by ``;``::

    ref=NL-778899;status=in_transit;time=2024-03-04T14:30:00-06:00;city=Dallas;state=TX
"""

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional

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


NORTHLINE_REQUIRED = ("ref", "status", "time", "city")
_NORTHLINE_REFERENCE = re.compile(r"NL-\d{6}")
_NORTHLINE_TIME = re.compile(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(Z|[+-]\d{2}:\d{2})?")


def _northline_time(value: str) -> datetime:
    """Return a Northline timestamp as a naive UTC ``datetime``."""
    match = _NORTHLINE_TIME.fullmatch(value)
    if match is None:
        raise ValueError(f"invalid time: {value}")
    stamp, offset = match.groups()
    try:
        moment = datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%S")
    except ValueError:
        raise ValueError(f"invalid time: {value}") from None
    if offset and offset != "Z":
        sign = 1 if offset[0] == "+" else -1
        minutes = int(offset[1:3]) * 60 + int(offset[4:6])
        moment -= sign * timedelta(minutes=minutes)
    return moment


def parse_northline(message: str) -> StatusUpdate:
    """Parse one Northline ``key=value;key=value`` message into a ``StatusUpdate``.

    Raises ``ValueError`` when the message is malformed.
    """
    pairs: Dict[str, str] = {}
    for piece in message.split(";"):
        piece = piece.strip()
        if not piece:
            continue
        key, separator, value = piece.partition("=")
        key = key.strip().lower()
        if not separator or not key:
            raise ValueError(f"malformed pair: {piece}")
        if key in pairs:
            raise ValueError(f"duplicate key: {key}")
        pairs[key] = value.strip()
    for key in NORTHLINE_REQUIRED:
        if not pairs.get(key):
            raise ValueError(f"missing field: {key}")
    reference = pairs["ref"]
    if not _NORTHLINE_REFERENCE.fullmatch(reference.upper()):
        raise ValueError(f"invalid reference: {reference}")
    try:
        status = StatusCode[pairs["status"].upper()]
    except KeyError:
        raise ValueError(f"unknown status: {pairs['status']}") from None
    timestamp = _northline_time(pairs["time"])
    location = pairs["city"]
    if pairs.get("state"):
        location = f"{location}, {pairs['state']}"
    return StatusUpdate(reference.upper(), status, timestamp, location, pairs.get("note") or None)


def parse_message(text: str) -> StatusUpdate:
    """Parse one message from either carrier.

    A message that starts with ``ref=`` (in any letter case) is a Northline
    message. Anything else is a Carrier FX message.
    """
    if text.lstrip()[:4].lower() == "ref=":
        return parse_northline(text)
    return parse_status(text)


def parse_batch(text: str) -> List[StatusUpdate]:
    """Parse a block of messages from either carrier, one per line. Blank lines are skipped.

    A bad line raises ``ValueError`` whose message starts with the line number,
    for example ``line 3: missing location``.
    """
    updates: List[StatusUpdate] = []
    for number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            updates.append(parse_message(line))
        except ValueError as error:
            raise ValueError(f"line {number}: {error}") from None
    return updates
