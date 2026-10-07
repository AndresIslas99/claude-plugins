"""Delivery estimates in business days (Monday to Friday)."""

import math
from datetime import date, timedelta
from typing import Dict

from freightlib.validation import validate_miles, validate_service

MILES_PER_DAY: Dict[str, int] = {"standard": 500, "bulk": 400, "expedited": 750}


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


def transit_business_days(miles: float, service: str = "standard") -> int:
    """Return the business days a truck needs to cover ``miles`` miles.

    A truck covers a fixed number of miles each business day. A day that is only
    partly used still counts as a whole day.
    """
    validate_miles(miles)
    per_day = MILES_PER_DAY[validate_service(service)]
    return math.ceil(miles / per_day)


def estimate_delivery(pickup: date, miles: float, service: str = "standard") -> date:
    """Return the estimated delivery date for a shipment picked up on ``pickup``."""
    return add_business_days(pickup, transit_business_days(miles, service))
