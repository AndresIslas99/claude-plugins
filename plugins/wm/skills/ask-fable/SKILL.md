---
name: ask-fable
description: Consult wm:fable-advisor, the most capable model at 5x Sonnet's cost, on a problem of extreme complexity. Works through a self-contained dossier in the project's consults directory, then turns the advisor's memo into a decision with the user. Use it only when the T4 criteria hold; the user approves every call.
argument-hint: "<problem>"
---

# Ask Fable: $ARGUMENTS

This project's configuration (`.claude/working-model.json`):

!`cat "${CLAUDE_PROJECT_DIR}/.claude/working-model.json" 2>/dev/null || echo "None: consults go to docs/consults/ by default."`

1. **Check the criteria.** The problem must be T4: security-critical design, tenant isolation, concurrency or data integrity, an irreversible data-model choice, real-time systems, or something you have failed to solve twice. If it isn't T4, say so and solve it yourself: large or tedious isn't the same as hard.
2. **Write the dossier.** Create `NNNN-short-title.md` in the consults directory (`paths.consults`, by default `docs/consults`), with the next free number, from the `template.md` there, and give it the status `Open`. The advisor knows nothing of this conversation, so the dossier must stand on its own. Keep it lean: point to `path:line` and decision records instead of pasting code, and say exactly what form of answer you need.
3. **Call the advisor.** Call `Agent` with `subagent_type: "wm:fable-advisor"` and a `description` that tells the user what they're approving. Use the prompt `Read the dossier in <path>, write your memo in its Memo section, and reply with a summary of at most ten lines.`
   - The user is asked to approve the call. If they decline, continue without the advisor and say what is at risk.
   - The effort defaults to high. Pass `effort: "xhigh"` for security or integrity proofs.
4. **Follow up** by sending the same advisor more questions with `SendMessage`, instead of opening a new consult; it keeps its context.
5. **Assess.** Read the memo critically, and check its claims against the code and the decisions; the advisor can be wrong. Write the "Lead's assessment" section: what you agree with, what you don't and why, and the decision you recommend. Set the status to `Answered`.
6. **Decide with the user.** Present the recommendation, its main risk and your assessment. Record the decision in a decision record that links the consult, then set the consult's status to `Decided (<record>)` or `Dropped`.
