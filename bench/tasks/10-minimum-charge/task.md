Finance raised our minimum charge from $85.00 to $95.00. Please update `MINIMUM_CHARGE` in `transferlib/rates.py`.

While you are in there: the minimum charge is supposed to apply to every service level, but small priority transfers are not getting it. A 10 GB priority transfer comes out at $34.00 and it should be $95.00. For every service level, `calc_rate` must never return less than the minimum charge. Charges that are already above the minimum must stay exactly as they are.

Replicated transfers and quotes are built on `calc_rate`, so they should follow: a small replicated transfer is priced from the $95.00 first-copy charge, and the transfer line on a small quote is $95.00 for every service level.
