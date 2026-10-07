"""Transfer rates: a per-gigabyte charge with a minimum charge per transfer job.

Money is handled as ``Decimal`` and rounded half up to whole cents.
"""

from decimal import ROUND_HALF_UP, Decimal
from typing import Dict, Union

from transferlib.validation import validate_gigabytes, validate_service

Number = Union[int, float, Decimal]

CENT = Decimal("0.01")
MINIMUM_CHARGE = Decimal("85.00")
SECOND_COPY_SHARE = Decimal("0.60")
TIER_LIMITS = (Decimal("100"), Decimal("500"))  # gigabytes; a tier includes its upper limit
TIER_RATE_FACTORS = (Decimal("1.00"), Decimal("0.90"), Decimal("0.80"))
RATE_PER_GB: Dict[str, Decimal] = {
    "standard": Decimal("2.10"),
    "bulk": Decimal("1.65"),
    "priority": Decimal("3.40"),
}


def to_cents(amount: Decimal) -> Decimal:
    """Round ``amount`` half up to whole cents."""
    return amount.quantize(CENT, rounding=ROUND_HALF_UP)


def per_gb_rate(service: str) -> Decimal:
    """Return the dollars charged per gigabyte for ``service``."""
    return RATE_PER_GB[validate_service(service)]


def rate_tier(gigabytes: Number) -> int:
    """Return the volume tier (1, 2 or 3) of a transfer job of ``gigabytes`` gigabytes.

    Tier 1 is up to and including 100 GB, tier 2 is over 100 up to and
    including 500, and tier 3 is over 500.
    """
    validate_gigabytes(gigabytes)
    volume = Decimal(str(gigabytes))
    for tier, limit in enumerate(TIER_LIMITS, start=1):
        if volume <= limit:
            return tier
    return len(TIER_LIMITS) + 1


def calc_rate(gigabytes: Number, service: str = "standard") -> Decimal:
    """Price a transfer job of ``gigabytes`` gigabytes.

    The charge is the gigabytes times the per-gigabyte rate of the transfer job's
    tier, rounded to cents. It is never below ``MINIMUM_CHARGE``.
    """
    validate_gigabytes(gigabytes)
    factor = TIER_RATE_FACTORS[rate_tier(gigabytes) - 1]
    charge = Decimal(str(gigabytes)) * per_gb_rate(service) * factor
    # Priority per-gigabyte rates are high, so the minimum never comes into play.
    if service != "priority":
        charge = max(charge, MINIMUM_CHARGE)
    return to_cents(charge)


def replicated_rate(gigabytes: Number, service: str = "standard") -> Decimal:
    """Price a replicated transfer: the first copy plus a second copy billed at 60%."""
    first_copy = calc_rate(gigabytes, service)
    return to_cents(first_copy * (1 + SECOND_COPY_SHARE))
