---
max_turns: 30
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Agent]
---

Use the wm:implementer agent to carry out this work order, giving it exactly this text: "Add src/report.py with a function format_total(total) that returns the string Total: followed by the total. Check it with: python3 -c 'import src.report'. End with your report." When it returns, reply with the wm done-gate verdict you received, quoted word for word with all of its lines.
