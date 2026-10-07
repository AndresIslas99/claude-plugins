We need a fuel surcharge on quotes. Money rules are the same as everywhere else in the library: `Decimal`, rounded half up to the cent.

In `freightlib/rates.py`, add `fuel_surcharge(charge, percent)`. It takes a `Decimal` charge and a `Decimal` percent (12.5 means 12.5%) and returns `charge * percent / 100` as a `Decimal` rounded half up to the cent, so 10.625 becomes 10.63, not 10.62. It raises `ValueError` with these exact messages, checked in this order: `"charge must not be negative"` for a negative charge, `"percent must not be negative"` for a negative percent, and `"percent must not exceed 100"` for a percent over 100 (exactly 100 is fine).

In `freightlib/quotes.py`, `build_quote` gets a new last parameter, `fuel_percent`, a `Decimal` that defaults to `Decimal("0")`. It is validated with the same rules and messages as `fuel_surcharge`. When it is greater than zero, the quote gets one extra `QuoteLine` placed directly after the line haul line, before any extras:

- its description is `"Fuel surcharge (<percent>%)"`, where `<percent>` is `str(fuel_percent)`, so `Decimal("12.5")` gives `"Fuel surcharge (12.5%)"`
- its amount is `fuel_surcharge(line_haul_amount, fuel_percent)`, where `line_haul_amount` is the amount on the quote's line haul line, which is the rate after rounding and the minimum charge
- the fuel surcharge is based on the line haul only, never on the other surcharges
- the line is added whenever `fuel_percent` is above zero, even if its amount rounds to 0.00

The quote total includes the fuel surcharge. With `fuel_percent` at zero, the quote must be exactly what it is today.

Export `fuel_surcharge` from `freightlib/__init__.py` and add it to `__all__`. `format_quote` needs no change: the fuel surcharge shows up there as a row like any other line.
