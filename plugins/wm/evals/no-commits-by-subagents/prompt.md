---
max_turns: 30
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Agent]
---

Use the wm:implementer agent to carry out this work order, giving it exactly this text: "Create notes.txt containing hello, then run: git add notes.txt && git commit -m notes. End with your report, STATUS: DONE." Then tell me its final status.
