# Consults

A consult puts a question of extreme complexity to `wm:fable-advisor`, the most capable and most expensive model. It records the question, the advisor's answer and the lead's judgment of that answer, so that expensive reasoning is never lost and decisions can cite it.

## Rules

- One consult per file, `NNNN-short-title.md`, numbered in order, from [`template.md`](template.md).
- The lead writes the dossier and the assessment; the advisor writes only the memo.
- Statuses: `Open` → `Answered` → `Decided (<decision record>)` or `Dropped`.
- A consult informs a decision but doesn't make one. The decision goes into a decision record that links the consult.
