Add a `validate_dimensions(length_in, width_in, height_in)` function to `freightlib/validation.py`. It checks the size of a box given in inches. It returns `None` when the box is acceptable and otherwise raises `ValueError` with one of these exact messages, where `<name>` is `length`, `width` or `height`:

- `"<name> must be positive"` when the value is zero, negative or NaN
- `"<name> must not exceed 636 inches"` when the value is over 636 (the inside length of a 53 foot trailer). Exactly 636 is allowed, and infinity counts as over the limit.

Check the sides in the order length, width, height. For each side, check that it is positive first and then check the limit, and stop at the first problem. So `(700, 0, 10)` reports the length limit, and `(10, 0, 700)` reports that the width must be positive.
