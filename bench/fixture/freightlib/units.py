"""Weight and volume conversions.

Every conversion rounds its result to 4 decimal places and raises ``ValueError``
when its input is negative.
"""

KG_PER_LB = 0.45359237
CUBIC_METERS_PER_CUBIC_FOOT = 0.028316846592
DIM_DIVISOR = 139  # cubic inches per billable pound


def _check_not_negative(value: float, name: str) -> None:
    """Raise ValueError if ``value`` is below zero."""
    if value < 0:
        raise ValueError(f"{name} must not be negative")


def lb_to_kg(pounds: float) -> float:
    """Convert pounds to kilograms."""
    _check_not_negative(pounds, "pounds")
    return round(pounds * KG_PER_LB, 4)


def kg_to_lb(kilograms: float) -> float:
    """Convert kilograms to pounds."""
    _check_not_negative(kilograms, "kilograms")
    return round(kilograms / KG_PER_LB, 4)


def cubic_feet_to_cubic_meters(cubic_feet: float) -> float:
    """Convert cubic feet to cubic meters."""
    _check_not_negative(cubic_feet, "cubic feet")
    return round(cubic_feet * CUBIC_METERS_PER_CUBIC_FOOT, 4)


def cubic_meters_to_cubic_feet(cubic_meters: float) -> float:
    """Convert cubic meters to cubic feet."""
    _check_not_negative(cubic_meters, "cubic meters")
    return round(cubic_meters / CUBIC_METERS_PER_CUBIC_FOOT, 4)


def dimensional_weight_lb(
    length_in: float, width_in: float, height_in: float, divisor: int = DIM_DIVISOR
) -> float:
    """Return the dimensional (volume based) weight of a box, in pounds.

    The dimensions are in inches. The volume in cubic inches is divided by ``divisor``.
    """
    for name, value in (("length", length_in), ("width", width_in), ("height", height_in)):
        _check_not_negative(value, name)
    return round(length_in * width_in * height_in / divisor, 4)
