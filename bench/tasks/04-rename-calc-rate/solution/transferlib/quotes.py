"""Quotes: the transfer rate plus the options a customer asked for."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, Iterable, List, Tuple

from transferlib.rates import Number, job_rate
from transferlib.validation import validate_gigabytes, validate_service, validate_size_gb

OPTIONS: Dict[str, Decimal] = {
    "encryption": Decimal("35.00"),
    "compression": Decimal("28.50"),
    "compliance": Decimal("75.00"),
}


@dataclass(frozen=True)
class QuoteLine:
    """One charge on a quote."""

    description: str
    amount: Decimal


@dataclass(frozen=True)
class Quote:
    """A priced transfer job: its charge lines and their total."""

    service: str
    gigabytes: Number
    size_gb: Number
    lines: Tuple[QuoteLine, ...]
    total: Decimal


def build_quote(
    gigabytes: Number,
    size_gb: Number,
    service: str = "standard",
    extras: Iterable[str] = (),
) -> Quote:
    """Price a transfer job.

    The first line is the transfer charge from ``job_rate``. Each name in ``extras``
    adds one option line from ``OPTIONS``, in the order given. The total is
    the sum of all lines. An unknown or repeated option raises ``ValueError``.
    """
    validate_gigabytes(gigabytes)
    validate_size_gb(size_gb)
    validate_service(service)
    lines: List[QuoteLine] = [
        QuoteLine(f"Transfer ({service})", job_rate(gigabytes, service))
    ]
    seen = set()
    for name in extras:
        if name not in OPTIONS:
            raise ValueError(f"unknown option: {name}")
        if name in seen:
            raise ValueError(f"duplicate option: {name}")
        seen.add(name)
        lines.append(QuoteLine(name.capitalize(), OPTIONS[name]))
    total = sum((line.amount for line in lines), Decimal("0.00"))
    return Quote(service, gigabytes, size_gb, tuple(lines), total)


def format_quote(quote: Quote) -> str:
    """Render a quote as plain text: one row per charge, then the total."""
    rows = [f"{line.description:<28}{line.amount:>10.2f}" for line in quote.lines]
    rows.append(f"{'Total':<28}{quote.total:>10.2f}")
    return "\n".join(rows)
