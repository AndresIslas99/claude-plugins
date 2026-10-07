---
name: doctor
description: Check that the wm working model is set up and working in this project - the hooks' scripts and Python, the Claude Code version, .claude/working-model.json (gate commands, globs, lead-owned files), the model routing, and recent receipts of the hooks' decisions and failures. Use it when the working model seems off, after changing its configuration, or before trusting the gates.
---

# wm doctor

!`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/doctor.py" "${CLAUDE_PROJECT_DIR}" 2>&1 || true`

Summarize this report for the user, the most serious problem first, each with its fix. "✗" is a problem, "!" is a warning, and "✓" is fine. Don't change any file until the user approves a fix.
