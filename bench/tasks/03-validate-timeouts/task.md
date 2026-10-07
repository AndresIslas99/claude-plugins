Add a `validate_timeouts(connect_s, read_s, total_s)` function to `transferlib/validation.py`. It checks the three timeouts of a transfer request, given in seconds. It returns `None` when the timeouts are acceptable and otherwise raises `ValueError` with one of these exact messages, where `<name>` is `connect`, `read` or `total`:

- `"<name> must be positive"` when the value is zero, negative or NaN
- `"<name> must not exceed 636 seconds"` when the value is over 636 (the longest timeout a provider accepts). Exactly 636 is allowed, and infinity counts as over the limit.

Check the timeouts in the order connect, read, total. For each timeout, check that it is positive first and then check the limit, and stop at the first problem. So `(700, 0, 10)` reports the connect limit, and `(10, 0, 700)` reports that the read timeout must be positive.
