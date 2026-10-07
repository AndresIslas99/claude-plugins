## Working model

This project follows the wm working model ({{DECISION_LINK}}). Decisions get the strongest reasoning, and code is written at the lowest cost that keeps its quality.

| Role | Model | Does |
|---|---|---|
| Lead: the main session | Opus | Talks with the user, decides, writes decided code, decisions and rules, reviews and commits |
| `wm:implementer` | Sonnet | Carries out one work order, when delegating pays: tests first, code, green gates, a fixed-format report |
| `wm:reviewer` | Opus | Reviews a risky diff against its request or work order, the rules and the decisions, with a fresh context |
| `wm:fable-advisor` | Fable | Writes decision memos on extreme problems, after two failed attempts by the lead; the user approves every call |
| `wm:scout` | Haiku | Searches the codebase and answers with `path:line` pointers |
| `wm:researcher` | Sonnet | Researches the web and reports dated sources |

Route every request by tier:

- **T0, trivial** (a few lines, no design choice): do it yourself and run the relevant gates.
- **T1, decided and small** (one layer, an existing pattern): do it yourself, inline, and run the gates. There's no work order and no subagent.
- **T2, decided and larger** (several files or layers, a new contract, well specified and verifiable): `/wm:implement` does it inline, with tests first and the gates, and with a `wm:reviewer` review when it touches authentication, authorization, secrets, tenant isolation, concurrency, data integrity, migrations or a new public contract. It delegates to `wm:implementer`, with a work order in `{{WORK_ORDERS}}/`, only when the change would flood the context, splits into parallel parts, or the user wants the order on record. {{COMMIT_POLICY}}
- **T3, a new decision:** `/wm:design-session` with the user.
- **T4, extreme** (security-critical design, data integrity, concurrency, irreversible designs): work it at xhigh effort with the user. Consult Fable with `/wm:ask-fable` only after two failed attempts.

The gates and the lead-owned files are in `.claude/working-model.json`. The plugin's hooks enforce them: the implementer can't report done, and the lead can't commit, while the gates fail.

Token discipline:

- Keep the main context for decisions and decided code. Send searches to `wm:scout` and web research to `wm:researcher`. Read a file yourself only when you know which lines you need.
- Never switch the session's model in the middle of a task, because caches are per model. Starting a subagent costs about 20K tokens, and delegating code costs the lead an order and a review, so code is delegated only when that pays.
- Continue the same subagent with `SendMessage` for follow-ups and fixes; it keeps its context. `/usage` shows the cost by model and by subagent.

Rules for everyone:

- **Gates are the evidence.** Nothing is done until the gates pass. Never weaken a gate with suppressions, skipped tests or loosened configuration; only the lead adds a suppression, with the reason in a comment.
- **Decisions live in {{DECISIONS}}.** An accepted decision is never rewritten; a new one supersedes it. A change that needs a decision nobody has made waits until it is made.
- **Commits** are Conventional Commits, made on a topic branch when the current branch is protected. Never use `--no-verify`, and never push unless the user asks.
