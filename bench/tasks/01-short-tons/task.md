Add a `lb_to_short_tons` function to `freightlib/units.py`. It converts pounds to short tons, where 1 short ton is 2,000 lb.

Follow the other conversions in that file: round the result to 4 decimal places with `round(value, 4)`, and raise `ValueError("pounds must not be negative")` for a negative input (zero is fine). Export it from `freightlib/__init__.py` the same way as the other conversions, including `__all__`.
