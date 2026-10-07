---
# The verdict reaches the lead, and it shows the gate ran the project's own lint on the
# implementer's changes, although the order named only an import check.
type: regex
pattern: "wm done-gate: PASSED\\. It checked 1 changed file with `python3 fake_lint\\.py`"
arm: with-only
---
