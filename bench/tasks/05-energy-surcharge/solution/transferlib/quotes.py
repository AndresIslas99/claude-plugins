"""Quotes: the transfer rate plus the options a customer asked for."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, Iterable, List, Tuple

from transferlib.rates import Number, calc_rate, energy_surcharge
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
    energy_percent: Decimal = Decimal("0"),
) -> Quote:
    """Price a transfer job.

    The first line is the transfer charge from ``calc_rate``. When ``energy_percent`` is
    above zero, an energy surcharge line follows it, based on the transfer charge only.
    Each name in ``extras`` then adds one option line from ``OPTIONS``, in the
    order given. The total is the sum of all lines. An unknown or repeated
    option, or an invalid ``energy_percent``, raises ``ValueError``.
    """
    validate_gigabytes(gigabytes)
    validate_size_gb(size_gb)
    validate_service(service)
    transfer_charge = calc_rate(gigabytes, service)
    energy = energy_surcharge(transfer_charge, energy_percent)
    lines: List[QuoteLine] = [QuoteLine(f"Transfer ({service})", transfer_charge)]
    if energy_percent > 0:
        lines.append(QuoteLine(f"Energy surcharge ({energy_percent}%)", energy))
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
