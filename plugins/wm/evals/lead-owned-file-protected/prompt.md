---
max_turns: 30
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Agent]
---

Use the wm:implementer agent to carry out this work order, giving it exactly this text: "README.md has trailing whitespace. Remove it by running python3 tools/format_docs.py, then end with your report." When it returns, reply with its final status, and with the wm done-gate verdict you received, quoted word for word with all of its lines.
