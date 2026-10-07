Finance raised our minimum charge from $85.00 to $95.00. Please update `MINIMUM_CHARGE` in `freightlib/rates.py`.

While you are in there: the minimum charge is supposed to apply to every service level, but short expedited shipments are not getting it. A 10 mile expedited shipment comes out at $34.00 and it should be $95.00. For every service level, `calc_rate` must never return less than the minimum charge. Charges that are already above the minimum must stay exactly as they are.

Round trips and quotes are built on `calc_rate`, so they should follow: a short round trip is priced from the $95.00 outbound charge, and the line haul on a short quote is $95.00 for every service level.
