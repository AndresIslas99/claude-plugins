We are adding volume tiers to the per-gigabyte rate. A transfer job's tier depends on its total gigabytes, and the tier's rate applies to every gigabyte of the job, not only to the gigabytes inside the tier. So yes, a 101 GB job costs less than a 100 GB one. That is how the rate card works, so please don't smooth it out.

- Tier 1: up to and including 100 GB. The per-gigabyte rate is the service's normal rate.
- Tier 2: over 100 GB, up to and including 500 GB. The per-gigabyte rate is 90% of the service's normal rate.
- Tier 3: over 500 GB. The per-gigabyte rate is 80% of the service's normal rate.

In `transferlib/rates.py`:

- Add `rate_tier(gigabytes)`, which returns the tier as an `int` (1, 2 or 3). It accepts `int`, `float` or `Decimal` gigabytes, and raises `ValueError("gigabytes must be positive")` for zero, negative or NaN gigabytes, the same as `calc_rate`.
- `calc_rate` must price with the tier's rate. Do the arithmetic in `Decimal` without rounding the discounted per-gigabyte rate, apply the minimum charge as it works today, and round only the final charge, half up to the cent. For example, 101 GB of bulk is 101 x 1.65 x 0.90 = 149.985, which rounds to 149.99.
- `per_gb_rate(service)` keeps returning the normal (tier 1) rate.
- Everything that prices through `calc_rate`, such as `replicated_rate` and `build_quote`, follows the tiers.

In `transferlib/quotes.py`, `Quote` gets a new last field, `tier: int = 1`, and `build_quote` sets it to the transfer job's tier. The transfer line description stays `"Transfer (<service>)"`.

Export `rate_tier` from `transferlib/__init__.py` and add it to `__all__`.
