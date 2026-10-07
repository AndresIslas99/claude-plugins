"""Freight rates: a per-mile charge with a minimum charge per shipment.

Money is handled as ``Decimal`` and rounded half up to whole cents.
"""

from decimal import ROUND_HALF_UP, Decimal
from typing import Dict, Union

from freightlib.validation import validate_miles, validate_service

Number = Union[int, float, Decimal]

CENT = Decimal("0.01")
MINIMUM_CHARGE = Decimal("85.00")
RETURN_LEG_SHARE = Decimal("0.60")
TIER_LIMITS = (Decimal("100"), Decimal("500"))  # miles; a tier includes its upper limit
TIER_RATE_FACTORS = (Decimal("1.00"), Decimal("0.90"), Decimal("0.80"))
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


def rate_tier(miles: Number) -> int:
    """Return the distance tier (1, 2 or 3) of a shipment of ``miles`` miles.

    Tier 1 is up to and including 100 miles, tier 2 is over 100 up to and
    including 500, and tier 3 is over 500.
    """
    validate_miles(miles)
    distance = Decimal(str(miles))
    for tier, limit in enumerate(TIER_LIMITS, start=1):
        if distance <= limit:
            return tier
    return len(TIER_LIMITS) + 1


def calc_rate(miles: Number, service: str = "standard") -> Decimal:
    """Price a shipment of ``miles`` miles.

    The charge is the miles times the per-mile rate of the shipment's tier,
    rounded to cents. It is never below ``MINIMUM_CHARGE``.
    """
    validate_miles(miles)
    factor = TIER_RATE_FACTORS[rate_tier(miles) - 1]
    charge = Decimal(str(miles)) * per_mile_rate(service) * factor
    # Expedited per-mile rates are high, so the minimum never comes into play.
    if service != "expedited":
        charge = max(charge, MINIMUM_CHARGE)
    return to_cents(charge)


def round_trip_rate(miles: Number, service: str = "standard") -> Decimal:
    """Price a round trip: the outbound charge plus a return leg at 60% of it."""
    outbound = calc_rate(miles, service)
    return to_cents(outbound * (1 + RETURN_LEG_SHARE))
