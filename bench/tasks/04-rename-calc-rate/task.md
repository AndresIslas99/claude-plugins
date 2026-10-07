`calc_rate` in `freightlib/rates.py` has a poor name. Rename it to `shipment_rate`, with the same arguments and the same behavior, and update everything in the library that calls it (`round_trip_rate` in `rates.py` and `build_quote` in `quotes.py`). Export `shipment_rate` from `freightlib/__init__.py` and add it to `__all__`.

Keep `calc_rate` working as a deprecated alias. Calling it must emit one `DeprecationWarning` whose message mentions `shipment_rate`, reported against the file that called `calc_rate` (not against freightlib), and then return exactly what `shipment_rate` returns. `calc_rate` stays exported from the package. Library code must not call the deprecated name any more, so `round_trip_rate` and `build_quote` must not emit any warning.

Leave the files in `tests/` alone. They still call `calc_rate` and have to keep passing through the alias.
