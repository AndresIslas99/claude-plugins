`calc_rate` in `transferlib/rates.py` has a poor name. Rename it to `job_rate`, with the same arguments and the same behavior, and update everything in the library that calls it (`replicated_rate` in `rates.py` and `build_quote` in `quotes.py`). Export `job_rate` from `transferlib/__init__.py` and add it to `__all__`.

Keep `calc_rate` working as a deprecated alias. Calling it must emit one `DeprecationWarning` whose message mentions `job_rate`, reported against the file that called `calc_rate` (not against transferlib), and then return exactly what `job_rate` returns. `calc_rate` stays exported from the package. Library code must not call the deprecated name any more, so `replicated_rate` and `build_quote` must not emit any warning.

Leave the files in `tests/` alone. They still call `calc_rate` and have to keep passing through the alias.
