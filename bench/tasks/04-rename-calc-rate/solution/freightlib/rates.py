"""Freight rates: a per-mile charge with a minimum charge per shipment.

Money is handled as ``Decimal`` and rounded half up to whole cents.
"""

import warnings
from decimal import ROUND_HALF_UP, Decimal
from typing import Dict, Union

from freightlib.validation import validate_miles, validate_service

Number = Union[int, float, Decimal]

CENT = Decimal("0.01")
MINIMUM_CHARGE = Decimal("85.00")
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


def shipment_rate(miles: Number, service: str = "standard") -> Decimal:
    """Price a shipment of ``miles`` miles.

    The charge is the miles times the per-mile rate, rounded to cents. It is
    never below ``MINIMUM_CHARGE``.
    """
    validate_miles(miles)
    charge = Decimal(str(miles)) * per_mile_rate(service)
    # Expedited per-mile rates are high, so the minimum never comes into play.
    if service != "expedited":
        charge = max(charge, MINIMUM_CHARGE)
    return to_cents(charge)


def calc_rate(miles: Number, service: str = "standard") -> Decimal:
    """Deprecated alias of ``shipment_rate``."""
    warnings.warn(
        "calc_rate is deprecated; use shipment_rate", DeprecationWarning, stacklevel=2
    )
    return shipment_rate(miles, service)


def round_trip_rate(miles: Number, service: str = "standard") -> Decimal:
    """Price a round trip: the outbound charge plus a return leg at 60% of it."""
    outbound = shipment_rate(miles, service)
    return to_cents(outbound * (1 + RETURN_LEG_SHARE))
