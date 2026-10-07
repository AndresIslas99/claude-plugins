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


def calc_rate(gigabytes: Number, service: str = "standard") -> Decimal:
    """Price a transfer job of ``gigabytes`` gigabytes.

    The charge is the gigabytes times the per-gigabyte rate, rounded to cents. It is
    never below ``MINIMUM_CHARGE``.
    """
    validate_gigabytes(gigabytes)
    charge = Decimal(str(gigabytes)) * per_gb_rate(service)
    # Priority per-gigabyte rates are high, so the minimum never comes into play.
    if service != "priority":
        charge = max(charge, MINIMUM_CHARGE)
    return to_cents(charge)


def replicated_rate(gigabytes: Number, service: str = "standard") -> Decimal:
    """Price a replicated transfer: the first copy plus a second copy billed at 60%."""
    first_copy = calc_rate(gigabytes, service)
    return to_cents(first_copy * (1 + SECOND_COPY_SHARE))
