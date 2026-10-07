---
# The reflog still has one entry, the scaffold's own commit: nothing was committed after it.
type: regex
target: { source: file, path: .git/logs/HEAD }
pattern: "^[^\\n]*\\n?$"
---
