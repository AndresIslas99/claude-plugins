Add a `gb_to_tb` function to `transferlib/units.py`. It converts gigabytes to terabytes, where 1 terabyte is 1,000 GB.

Follow the other conversions in that file: round the result to 4 decimal places with `round(value, 4)`, and raise `ValueError("gigabytes must not be negative")` for a negative input (zero is fine). Export it from `transferlib/__init__.py` the same way as the other conversions, including `__all__`.
