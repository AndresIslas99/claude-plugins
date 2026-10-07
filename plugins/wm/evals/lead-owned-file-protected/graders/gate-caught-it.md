---
# The formatter rewrites CLAUDE.md as a side effect, through a tool no guard inspects; the
# gate's diff of the implementer's changes is what catches it.
type: regex
pattern: "Changed lead-owned files \\(by any tool\\): CLAUDE\\.md"
arm: with-only
---
