We now also get status messages from a second provider, Northline, in a different format. Please add support for it in `transferlib/parsing.py`. The existing Provider FX parsing must keep working as it does now.

A Northline message is one line of `key=value` pairs separated by `;`, for example:

    ref=NL-778899;status=in_transfer;time=2024-03-04T14:30:00-06:00;region=us-east-1;zone=az-a;note=Left the queue

Add `parse_northline(message)`, which returns a `StatusUpdate` (the same dataclass the FX parser returns). The rules:

- Split the message on `;`. In each piece only the first `=` separates the key from the value, so a note may contain `=`. Trim whitespace around keys and values. Keys are case-insensitive. Pieces that are empty after trimming are ignored (a trailing `;` is fine). Keys other than the ones below are ignored.
- A piece with no `=`, or with a blank key, raises `ValueError("malformed pair: <piece>")`, using the trimmed piece. A key that appears twice (compared in lower case, and including keys that are otherwise ignored) raises `ValueError("duplicate key: <key>")`, using the lower-case key.
- The required keys are `ref`, `status`, `time` and `region`. If one is missing, or its value is blank, raise `ValueError("missing field: <key>")`, for the first such key in that order.
- `ref` is `NL-` followed by exactly six digits. The `NL` may be in any letter case, and the result is upper-cased: `nl-778899` becomes `NL-778899`. Anything else raises `ValueError("invalid reference: <value>")`, with the trimmed value as it was given.
- `status` is the name of a `StatusCode` member in any letter case: `pulled`, `in_transfer`, `on_disk`, `delivered` or `exception`. Anything else raises `ValueError("unknown status: <value>")`, with the trimmed value as it was given.
- `time` must be `YYYY-MM-DDTHH:MM:SS`, optionally followed directly by `Z`, `+HH:MM` or `-HH:MM`. All of the date, the `T`, the hours, minutes and seconds are required, and nothing else is allowed (no fractions of a second). The result is a naive `datetime` (no `tzinfo`) in UTC. Apply the offset, so `2024-03-04T14:30:00-06:00` becomes `datetime(2024, 3, 4, 20, 30)`. A time with `Z` or with no suffix is already UTC. A value that does not fit this shape, or is not a real date and time, raises `ValueError("invalid time: <value>")`, with the trimmed value as it was given.
- The location is `"<region>, <zone>"` when `zone` is present and not blank, and otherwise just `"<region>"`.
- `note` is optional. A missing or blank note becomes `None`.

If a message has several problems, report the first of these: a malformed pair or duplicate key (reading the pieces from left to right), a missing field, an invalid reference, an unknown status, an invalid time.

Also add `parse_message(text)`, which parses one message from either provider. If the text, after trimming leading whitespace, starts with `ref=` in any letter case, it is a Northline message and goes to `parse_northline`. Anything else goes to `parse_status`, errors included. Change `parse_batch` to use `parse_message` for each line, keeping its skipping of blank lines and its `line N: ` prefix on errors.

Export `parse_northline` and `parse_message` from `transferlib/__init__.py` and add them to `__all__`.
