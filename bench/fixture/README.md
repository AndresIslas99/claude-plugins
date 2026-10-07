# transferlib

Small Python helpers for pricing and tracking data transfer jobs between cloud regions. It
uses only the standard library and runs on Python 3.9.

## Modules

| Module | What it does |
|---|---|
| `transferlib/units.py` | Gigabyte and terabyte conversions |
| `transferlib/rates.py` | Per-gigabyte transfer rates with a minimum charge |
| `transferlib/eta.py` | Delivery estimates in business days (Monday to Friday) |
| `transferlib/validation.py` | Input checks that raise `ValueError` |
| `transferlib/parsing.py` | Parses provider status messages into dataclasses |
| `transferlib/quotes.py` | Builds a quote from a rate and options |

## Conventions

- Money is `Decimal`, rounded half up to whole cents.
- Unit conversions return floats rounded to 4 decimal places.
- Bad input raises `ValueError` with a short lowercase message.
- Public names are re-exported from `transferlib/__init__.py` and listed in `__all__`.

## Tests

```bash
python3 -m unittest discover -s tests -q
```
