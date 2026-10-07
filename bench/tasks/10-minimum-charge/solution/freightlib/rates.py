"""Freight rates: a per-mile charge with a minimum charge per shipment.

Money is handled as ``Decimal`` and rounded half up to whole cents.
"""

from decimal import ROUND_HALF_UP, Decimal
from typing import Dict, Union

from freightlib.validation import validate_miles, validate_service

Number = Union[int, float, Decimal]

CENT = Decimal("0.01")
MINIMUM_CHARGE = Decimal("95.00")
RETURN_LEG_SHARE = Decimal("0.60")
RATE_PER_MILE: Dict[str, Decimal] = {
    "standard": Decimal("2.10"),
    "bulk": Decimal("1.65"),
    "expedited": Decimal("3.40"),
}


def to_cents(amount: Decimal) -> Decimal:
    """Round ``amount`` half up to whole cents."""
    return amount.quantize(CENT, rounding=ROUND_HALF_UP)


def per_mile_rate(service: str) -> Decimal:
    """Return the dollars charged per mile for ``service``."""
    return RATE_PER_MILE[validate_service(service)]


def calc_rate(miles: Number, service: str = "standard") -> Decimal:
    """Price a shipment of ``miles`` miles.

    The charge is the miles times the per-mile rate, rounded to cents. It is
    never below ``MINIMUM_CHARGE``.
    """
    validate_miles(miles)
    charge = Decimal(str(miles)) * per_mile_rate(service)
    return to_cents(max(charge, MINIMUM_CHARGE))


def round_trip_rate(miles: Number, service: str = "standard") -> Decimal:
    """Price a round trip: the outbound charge plus a return leg at 60% of it."""
    outbound = calc_rate(miles, service)
    return to_cents(outbound * (1 + RETURN_LEG_SHARE))
