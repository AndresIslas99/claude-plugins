We need an energy surcharge on quotes. Money rules are the same as everywhere else in the library: `Decimal`, rounded half up to the cent.

In `transferlib/rates.py`, add `energy_surcharge(charge, percent)`. It takes a `Decimal` charge and a `Decimal` percent (12.5 means 12.5%) and returns `charge * percent / 100` as a `Decimal` rounded half up to the cent, so 10.625 becomes 10.63, not 10.62. It raises `ValueError` with these exact messages, checked in this order: `"charge must not be negative"` for a negative charge, `"percent must not be negative"` for a negative percent, and `"percent must not exceed 100"` for a percent over 100 (exactly 100 is fine).

In `transferlib/quotes.py`, `build_quote` gets a new last parameter, `energy_percent`, a `Decimal` that defaults to `Decimal("0")`. It is validated with the same rules and messages as `energy_surcharge`. When it is greater than zero, the quote gets one extra `QuoteLine` placed directly after the transfer line, before any extras:

- its description is `"Energy surcharge (<percent>%)"`, where `<percent>` is `str(energy_percent)`, so `Decimal("12.5")` gives `"Energy surcharge (12.5%)"`
- its amount is `energy_surcharge(transfer_amount, energy_percent)`, where `transfer_amount` is the amount on the quote's transfer line, which is the rate after rounding and the minimum charge
- the energy surcharge is based on the transfer line only, never on the options
- the line is added whenever `energy_percent` is above zero, even if its amount rounds to 0.00

The quote total includes the energy surcharge. With `energy_percent` at zero, the quote must be exactly what it is today.

Export `energy_surcharge` from `transferlib/__init__.py` and add it to `__all__`. `format_quote` needs no change: the energy surcharge shows up there as a row like any other line.
