"""Shipment validation helpers.

Each helper checks one input. It raises ``ValueError`` with a short message when
the input is bad and returns the cleaned value otherwise.
"""

import re
from typing import Tuple

SERVICES: Tuple[str, ...] = ("standard", "bulk", "expedited")
MAX_WEIGHT_LB = 45000
_POSTAL_CODE = re.compile(r"\d{5}")
_REFERENCE = re.compile(r"[A-Z]{2}\d{6}")


def validate_service(service: str) -> str:
    """Return ``service`` if it is a known service level."""
    if service not in SERVICES:
        raise ValueError(f"unknown service: {service}")
    return service


def validate_miles(miles: float) -> float:
    """Return ``miles`` if it is greater than zero."""
    if not miles > 0:
        raise ValueError("miles must be positive")
    return miles


def validate_weight_lb(weight_lb: float) -> float:
    """Return ``weight_lb`` if it is positive and within the legal truck limit."""
    if not weight_lb > 0:
        raise ValueError("weight must be positive")
    if weight_lb > MAX_WEIGHT_LB:
        raise ValueError(f"weight must not exceed {MAX_WEIGHT_LB} lb")
    return weight_lb


def validate_postal_code(code: str) -> str:
    """Return a five-digit US postal code with surrounding spaces removed."""
    cleaned = code.strip()
    if not _POSTAL_CODE.fullmatch(cleaned):
        raise ValueError(f"invalid postal code: {code!r}")
    return cleaned


def validate_reference(reference: str) -> str:
    """Return a carrier reference such as ``FX123456`` in upper case."""
    cleaned = reference.strip().upper()
    if not _REFERENCE.fullmatch(cleaned):
        raise ValueError(f"invalid reference: {reference!r}")
    return cleaned
