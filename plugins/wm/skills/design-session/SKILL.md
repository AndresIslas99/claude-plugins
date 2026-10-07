---
name: design-session
description: Run a design session with the wm working model, for a decision the project hasn't made yet - its architecture, a module's design, a data model, an integration, a platform choice. Frames the decision, researches it, weighs options, decides with the user, records it, encodes the rules and plans the work orders. Use it whenever a change needs a new decision, and when a new project needs its first ones.
argument-hint: "<topic>"
---

# Design session: $ARGUMENTS

This project's configuration (`.claude/working-model.json`):

!`cat "${CLAUDE_PROJECT_DIR}/.claude/working-model.json" 2>/dev/null || echo "None: this project hasn't adopted the working model. Offer /wm:adopt first; a design session works without it, but its decisions then need a home."`

You run this session with the user, as the lead. It produces decisions with their reasons, rules and a plan, not code. Decision records live in the configuration's `paths.decisions` directory; if the project keeps none yet, offer to start one with the session's first decision.

1. **Frame.** State the decisions to make, the forces behind them, and the existing decisions that constrain them. List what is already decided and won't be reopened. Confirm the framing with the user before researching.
2. **Research.**
   - Questions about the code go to `wm:scout`.
   - External facts (versions, support windows, prices, standards, laws, vendor capabilities) go to `wm:researcher`, with one agent per independent question, launched in parallel. Pass `effort: "high"` when the facts will decide the outcome.
   - Keep raw web pages and large files out of the main session; work from the agents' reports.
3. **Options.** Develop at least two serious options per decision, each with its costs. If a decision meets the T4 criteria (`/wm:implement` lists them), work it at xhigh effort, and run `/wm:ask-fable` only after two failed attempts.
4. **Decide with the user.** Present your recommendation and the strongest case against it, and use AskUserQuestion for real choices. Never record a decision the user hasn't made.
5. **Record.** Write one decision record per decision, following the project's own template and conventions: context with dated facts, the decision, consequences including the costs, and alternatives considered. Its status is `Proposed` until the user accepts it. An accepted record is never rewritten; a new one supersedes it.
6. **Encode.** Turn the decision's "how" into rules in `.claude/rules/`, scoped with `paths:` to the files they govern. Rules are short and imperative, and they cite their decision.
7. **Plan.** Break the work into work orders with the status `Draft`. Note their order, their dependencies, which can run in parallel, and which need contracts or tests written by the lead. Hand off to `/wm:implement`.

Run a session that is T4 from start to finish at xhigh effort (`/effort xhigh`): effort changes keep the cache, while model changes don't. Never switch models in the middle of a session.
