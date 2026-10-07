"""Transfer validation helpers.

Each helper checks one input. It raises ``ValueError`` with a short message when
the input is bad and returns the cleaned value otherwise.
"""

import re
from typing import Tuple

SERVICES: Tuple[str, ...] = ("standard", "bulk", "priority")
MAX_SIZE_GB = 45000
_ACCOUNT_NUMBER = re.compile(r"\d{5}")
_REFERENCE = re.compile(r"[A-Z]{2}\d{6}")


def validate_service(service: str) -> str:
    """Return ``service`` if it is a known service level."""
    if service not in SERVICES:
        raise ValueError(f"unknown service: {service}")
    return service


def validate_gigabytes(gigabytes: float) -> float:
    """Return ``gigabytes`` if it is greater than zero."""
    if not gigabytes > 0:
        raise ValueError("gigabytes must be positive")
    return gigabytes


def validate_size_gb(size_gb: float) -> float:
    """Return ``size_gb`` if it is positive and within the batch limit."""
    if not size_gb > 0:
        raise ValueError("size must be positive")
    if size_gb > MAX_SIZE_GB:
        raise ValueError(f"size must not exceed {MAX_SIZE_GB} GB")
    return size_gb


def validate_account_number(number: str) -> str:
    """Return a five-digit account number with surrounding spaces removed."""
    cleaned = number.strip()
    if not _ACCOUNT_NUMBER.fullmatch(cleaned):
        raise ValueError(f"invalid account number: {number!r}")
    return cleaned


def validate_reference(reference: str) -> str:
    """Return a provider reference such as ``FX123456`` in upper case."""
    cleaned = reference.strip().upper()
    if not _REFERENCE.fullmatch(cleaned):
        raise ValueError(f"invalid reference: {reference!r}")
    return cleaned
