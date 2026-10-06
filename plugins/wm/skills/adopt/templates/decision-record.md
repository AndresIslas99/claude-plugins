# NNNN. AI-assisted development with the wm working model

- **Status:** Proposed
- **Date:** YYYY-MM-DD

## Context

- The project is built with Claude Code. Anthropic's API list prices on 2026-10-06, per million tokens:

  | Model | Input / output | Relative to Sonnet |
  |---|---|---|
  | Fable 5.1 | $10 / $50 | 5× |
  | Opus 5.5 | $4 / $20 | 2× |
  | Sonnet 5.5 | $2 / $10 | 1× |
  | Haiku 4.5 | $1 / $5 | 0.5× |

- Most of the cost of writing code is output: the code itself and the reasoning behind it. Delegating to a cheaper model pays only when the handoff is precise; a vague handoff that needs two rounds of corrections costs more than having Opus do the work.
- A rule that isn't checked automatically erodes.

## Decision

We adopt the wm plugin's working model:
- the main session (Opus) leads and decides;
- `wm:implementer` (Sonnet) carries out precise work orders;
- `wm:reviewer` (Opus) reviews significant diffs;
- `wm:fable-advisor` (Fable) advises on problems of extreme complexity, with the user's approval for every call;
- `wm:scout` (Haiku) searches the code, and `wm:researcher` (Sonnet) researches the web.

Work is routed by tier (T0 to T4), as the project's `CLAUDE.md` describes. Instructions come in layers: decision records say why; rules in `.claude/rules/` say how; work orders in `{{WORK_ORDERS}}/` say what, for one change. The plugin's hooks enforce the gates in `.claude/working-model.json` and the agents' limits.

## Consequences

- Decisions get Opus or Fable. Code is written at Sonnet's price, and searches run at Haiku's.
- Every change leaves a trail from decision to work order to commit.
- A precise work order takes the lead's time and tokens, so trivial changes skip it.
- The workflow depends on the wm plugin and its hooks; the project keeps only its configuration, rules and documents.

## Alternatives considered

- **One model for everything:** the simplest option, but code costs more, and the main context fills up with it.
- **Instructions without hooks:** fewer moving parts, but they depend on models obeying.
