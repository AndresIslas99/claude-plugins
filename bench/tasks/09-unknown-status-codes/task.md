Carriers keep adding status codes we have never seen. Right now an unknown status code makes `parse_status` raise `ValueError("unknown status code: ...")`, and then `parse_batch` throws away the whole batch. That has to stop: an unknown status code must no longer be an error.

- Add a member `UNKNOWN = "??"` to `StatusCode`.
- Add a field `raw_code: Optional[str] = None` as the last field of `StatusUpdate`.
- When the status field of an FX message is not one of the five known codes (`PU`, `IT`, `OD`, `DL`, `EX`), `parse_status` returns a `StatusUpdate` whose `status` is `StatusCode.UNKNOWN` and whose `raw_code` is the status text, trimmed, exactly as it was sent. Matching stays exact and case-sensitive, so `it` is an unknown code, not `IT`. For the five known codes `raw_code` is `None`.
- An empty status field is still an error, now with the message `"missing status code"`.
- Everything else about parsing is unchanged. The checks still run in this order and each keeps its message: field count, status code (now only the empty check), timestamp, location, reference. So an unknown code does not hide a later problem in the same line.

`parse_batch` should simply keep the lines with unknown codes along with the others.
