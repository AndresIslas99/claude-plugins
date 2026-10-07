# freightlib

Small Python helpers for pricing and tracking freight shipments. It uses only the
standard library and runs on Python 3.9.

## Modules

| Module | What it does |
|---|---|
| `freightlib/units.py` | Weight and volume conversions |
| `freightlib/rates.py` | Per-mile freight rates with a minimum charge |
| `freightlib/eta.py` | Delivery estimates in business days (Monday to Friday) |
| `freightlib/validation.py` | Input checks that raise `ValueError` |
| `freightlib/parsing.py` | Parses carrier status messages into dataclasses |
| `freightlib/quotes.py` | Builds a quote from a rate and surcharges |

## Conventions

- Money is `Decimal`, rounded half up to whole cents.
- Unit conversions return floats rounded to 4 decimal places.
- Bad input raises `ValueError` with a short lowercase message.
- Public names are re-exported from `freightlib/__init__.py` and listed in `__all__`.

## Tests

```bash
python3 -m unittest discover -s tests -q
```
