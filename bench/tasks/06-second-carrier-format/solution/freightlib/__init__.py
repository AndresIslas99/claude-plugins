"""freightlib: pricing, tracking and validation helpers for freight shipments."""

from freightlib.eta import add_business_days, estimate_delivery, transit_business_days
from freightlib.parsing import (
    StatusCode,
    StatusUpdate,
    parse_batch,
    parse_message,
    parse_northline,
    parse_status,
)
from freightlib.quotes import Quote, QuoteLine, build_quote, format_quote
from freightlib.rates import calc_rate, per_mile_rate, round_trip_rate
from freightlib.units import (
    cubic_feet_to_cubic_meters,
    cubic_meters_to_cubic_feet,
    dimensional_weight_lb,
    kg_to_lb,
    lb_to_kg,
)
from freightlib.validation import (
    validate_miles,
    validate_postal_code,
    validate_reference,
    validate_service,
    validate_weight_lb,
)

__version__ = "0.4.0"

__all__ = [
    "Quote",
    "QuoteLine",
    "StatusCode",
    "StatusUpdate",
    "add_business_days",
    "build_quote",
    "calc_rate",
    "cubic_feet_to_cubic_meters",
    "cubic_meters_to_cubic_feet",
    "dimensional_weight_lb",
    "estimate_delivery",
    "format_quote",
    "kg_to_lb",
    "lb_to_kg",
    "parse_batch",
    "parse_message",
    "parse_northline",
    "parse_status",
    "per_mile_rate",
    "round_trip_rate",
    "transit_business_days",
    "validate_miles",
    "validate_postal_code",
    "validate_reference",
    "validate_service",
    "validate_weight_lb",
]
