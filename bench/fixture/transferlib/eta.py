"""Delivery estimates in business days (Monday to Friday)."""

from datetime import date, timedelta
from typing import Dict

from transferlib.validation import validate_gigabytes, validate_service

GB_PER_DAY: Dict[str, int] = {"standard": 500, "bulk": 400, "priority": 750}


def is_business_day(day: date) -> bool:
    """Return True if ``day`` is a Monday, Tuesday, Wednesday, Thursday or Friday."""
    return day.weekday() < 5


def add_business_days(start: date, days: int) -> date:
    """Return the date ``days`` business days after ``start``.

    Weekends are skipped and ``start`` itself is not counted. Adding zero days
    returns ``start`` unchanged, even when it falls on a weekend.
    """
    if days < 0:
        raise ValueError("days must not be negative")
    current = start
    remaining = days
    while remaining > 0:
        current += timedelta(days=1)
        if is_business_day(current):
            remaining -= 1
    return current


def transfer_business_days(gigabytes: float, service: str = "standard") -> int:
    """Return the business days a link needs to move ``gigabytes`` gigabytes.

    A link moves a fixed number of gigabytes each business day. A day that is only
    partly used still counts as a whole day.
    """
    validate_gigabytes(gigabytes)
    per_day = GB_PER_DAY[validate_service(service)]
    return int(gigabytes // per_day) + 1


def estimate_delivery(start: date, gigabytes: float, service: str = "standard") -> date:
    """Return the estimated delivery date for a transfer job started on ``start``."""
    return add_business_days(start, transfer_business_days(gigabytes, service))
