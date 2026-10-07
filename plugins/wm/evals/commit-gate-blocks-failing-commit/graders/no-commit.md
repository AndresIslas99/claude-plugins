---
# The reflog still has one entry, the scaffold's own commit.
type: regex
target: { source: file, path: .git/logs/HEAD }
pattern: "^[^\\n]*\\n?$"
arm: with-only
---
