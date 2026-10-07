We are adding distance tiers to the per-mile rate. A shipment's tier depends on its total miles, and the tier's rate applies to every mile of the shipment, not only to the miles inside the tier. So yes, a 101 mile shipment costs less than a 100 mile one. That is how the rate card works, so please don't smooth it out.

- Tier 1: up to and including 100 miles. The per-mile rate is the service's normal rate.
- Tier 2: over 100 miles, up to and including 500 miles. The per-mile rate is 90% of the service's normal rate.
- Tier 3: over 500 miles. The per-mile rate is 80% of the service's normal rate.

In `freightlib/rates.py`:

- Add `rate_tier(miles)`, which returns the tier as an `int` (1, 2 or 3). It accepts `int`, `float` or `Decimal` miles, and raises `ValueError("miles must be positive")` for zero, negative or NaN miles, the same as `calc_rate`.
- `calc_rate` must price with the tier's rate. Do the arithmetic in `Decimal` without rounding the discounted per-mile rate, apply the minimum charge as it works today, and round only the final charge, half up to the cent. For example, 101 miles of bulk is 101 x 1.65 x 0.90 = 149.985, which rounds to 149.99.
- `per_mile_rate(service)` keeps returning the normal (tier 1) rate.
- Everything that prices through `calc_rate`, such as `round_trip_rate` and `build_quote`, follows the tiers.

In `freightlib/quotes.py`, `Quote` gets a new last field, `tier: int = 1`, and `build_quote` sets it to the shipment's tier. The line haul description stays `"Line haul (<service>)"`.

Export `rate_tier` from `freightlib/__init__.py` and add it to `__all__`.
