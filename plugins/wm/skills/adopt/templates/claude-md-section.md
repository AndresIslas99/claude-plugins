## Working model

This project follows the wm working model ({{DECISION_LINK}}). Decisions get the strongest reasoning, and code is written at the lowest cost that keeps its quality.

| Role | Model | Does |
|---|---|---|
| Lead: the main session | Opus | Talks with the user, decides, writes decisions, rules and work orders, reviews and commits |
| `wm:implementer` | Sonnet | Carries out one work order: tests first, code, green gates, a fixed-format report |
| `wm:reviewer` | Opus | Reviews a diff against its work order, the rules and the decisions, with a fresh context |
| `wm:fable-advisor` | Fable | Writes decision memos on extreme problems, after two failed attempts by the lead; the user approves every call |
| `wm:scout` | Haiku | Searches the codebase and answers with `path:line` pointers |
| `wm:researcher` | Sonnet | Researches the web and reports dated sources |

Route every request by tier:

- **T0, trivial** (a few lines, no design choice): do it yourself and run the relevant gates.
- **T1, decided and small** (one layer, an existing pattern): do it yourself, inline, and run the gates. There's no work order and no subagent.
- **T2, decided and larger** (several files or layers, a new contract, well specified and verifiable): `/wm:implement`, with a work order in `{{WORK_ORDERS}}/`, the implementer, the gates, and a review. {{COMMIT_POLICY}}
- **T3, a new decision:** `/wm:design-session` with the user.
- **T4, extreme** (security-critical design, data integrity, concurrency, irreversible designs): work it at xhigh effort with the user. Consult Fable with `/wm:ask-fable` only after two failed attempts.

The gates and the lead-owned files are in `.claude/working-model.json`; the plugin's hooks enforce them.

Token discipline:

- Keep the main context for decisions. Send searches to `wm:scout`, web research to `wm:researcher`, and T2 code writing to `wm:implementer`. Read a file yourself only when you know which lines you need.
- Never switch the session's model in the middle of a task, because caches are per model; delegate instead. Starting a subagent costs about 20K tokens, so T0 and T1 work isn't worth delegating.
- Continue the same subagent with `SendMessage` for follow-ups and fixes; it keeps its context. `/usage` shows the cost by model and by subagent.

Rules for everyone:

- **Gates are the evidence.** Nothing is done until the gates pass. Never weaken a gate with suppressions, skipped tests or loosened configuration; only the lead adds a suppression, with the reason in a comment.
- **Decisions live in {{DECISIONS}}.** An accepted decision is never rewritten; a new one supersedes it. A change that needs a decision nobody has made waits until it is made.
- **Commits** are Conventional Commits, made on a topic branch when the current branch is protected. Never use `--no-verify`, and never push unless the user asks.
