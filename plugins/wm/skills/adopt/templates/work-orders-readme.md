# Work orders

A work order holds the lead's instructions for one unit of implementation: what to build, the exact contract, the rules that apply, and the tests that prove it. The lead, the main Claude Code session, writes it. `wm:implementer` carries it out, and the review checks the result against it.

Decision records say why. The rules in `.claude/rules/` say how, in general. A work order says what, for one change.

## Rules

- One work order per file, `NNNN-short-title.md`, numbered in order, from [`template.md`](template.md).
- Statuses: `Draft` → `Ready` → `In progress` → `Done`, or `Dropped`. Update the status line as the order moves.
- Only the lead writes or amends an order. An amendment made during implementation is noted in the order before the code follows it.
- An order is committed together with the change it describes, in one commit whose body says `Work order: NNNN`. A `Done` order isn't edited afterwards.

To list the orders and their statuses:

```bash
grep -H '^- \*\*Status' {{WORK_ORDERS}}/0*.md
```
