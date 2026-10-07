"""Gigabyte and terabyte conversions.

Every conversion rounds its result to 4 decimal places and raises ``ValueError``
when its input is negative.
"""

GIB_PER_GB = 0.9313225746154785  # 10**9 bytes in a GB over 2**30 bytes in a GiB
TIB_PER_TB = 0.9094947017729282  # 10**12 bytes in a TB over 2**40 bytes in a TiB
BLOCKS_PER_GB = 139  # blocks per billable gigabyte
GB_PER_TB = 1000


def _check_not_negative(value: float, name: str) -> None:
    """Raise ValueError if ``value`` is below zero."""
    if value < 0:
        raise ValueError(f"{name} must not be negative")


def gb_to_gib(gigabytes: float) -> float:
    """Convert gigabytes to gibibytes."""
    _check_not_negative(gigabytes, "gigabytes")
    return round(gigabytes * GIB_PER_GB, 4)


def gib_to_gb(gibibytes: float) -> float:
    """Convert gibibytes to gigabytes."""
    _check_not_negative(gibibytes, "gibibytes")
    return round(gibibytes / GIB_PER_GB, 4)


def gb_to_tb(gigabytes: float) -> float:
    """Convert gigabytes to terabytes (1 terabyte is 1,000 GB)."""
    _check_not_negative(gigabytes, "gigabytes")
    return round(gigabytes / GB_PER_TB, 4)


def tb_to_tib(terabytes: float) -> float:
    """Convert terabytes to tebibytes."""
    _check_not_negative(terabytes, "terabytes")
    return round(terabytes * TIB_PER_TB, 4)


def tib_to_tb(tebibytes: float) -> float:
    """Convert tebibytes to terabytes."""
    _check_not_negative(tebibytes, "tebibytes")
    return round(tebibytes / TIB_PER_TB, 4)


def billable_size_gb(
    rows: float, columns: float, layers: float, divisor: int = BLOCKS_PER_GB
) -> float:
    """Return the billable (volume based) size of a dataset, in gigabytes.

    The dimensions are counted in blocks. The volume in blocks is divided by ``divisor``.
    """
    for name, value in (("rows", rows), ("columns", columns), ("layers", layers)):
        _check_not_negative(value, name)
    return round(rows * columns * layers / divisor, 4)
