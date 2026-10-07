"""Quotes: the line haul rate plus the surcharges a customer asked for."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, Iterable, List, Tuple

from freightlib.rates import Number, calc_rate
from freightlib.validation import validate_miles, validate_service, validate_weight_lb

SURCHARGES: Dict[str, Decimal] = {
    "liftgate": Decimal("35.00"),
    "residential": Decimal("28.50"),
    "hazmat": Decimal("75.00"),
}


@dataclass(frozen=True)
class QuoteLine:
    """One charge on a quote."""

    description: str
    amount: Decimal


@dataclass(frozen=True)
class Quote:
    """A priced shipment: its charge lines and their total."""

    service: str
    miles: Number
    weight_lb: Number
    lines: Tuple[QuoteLine, ...]
    total: Decimal


def build_quote(
    miles: Number,
    weight_lb: Number,
    service: str = "standard",
    extras: Iterable[str] = (),
) -> Quote:
    """Price a shipment.

    The first line is the line haul from ``calc_rate``. Each name in ``extras``
    adds one surcharge line from ``SURCHARGES``, in the order given. The total is
    the sum of all lines. An unknown or repeated surcharge raises ``ValueError``.
    """
    validate_miles(miles)
    validate_weight_lb(weight_lb)
    validate_service(service)
    lines: List[QuoteLine] = [
        QuoteLine(f"Line haul ({service})", calc_rate(miles, service))
    ]
    seen = set()
    for name in extras:
        if name not in SURCHARGES:
            raise ValueError(f"unknown surcharge: {name}")
        if name in seen:
            raise ValueError(f"duplicate surcharge: {name}")
        seen.add(name)
        lines.append(QuoteLine(name.capitalize(), SURCHARGES[name]))
    total = sum((line.amount for line in lines), Decimal("0.00"))
    return Quote(service, miles, weight_lb, tuple(lines), total)


def format_quote(quote: Quote) -> str:
    """Render a quote as plain text: one row per charge, then the total."""
    rows = [f"{line.description:<28}{line.amount:>10.2f}" for line in quote.lines]
    rows.append(f"{'Total':<28}{quote.total:>10.2f}")
    return "\n".join(rows)
