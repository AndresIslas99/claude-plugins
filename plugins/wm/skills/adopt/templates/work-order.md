# NNNN. Short imperative title

- **Status:** Draft
- **Tier:** T1 | T2
- **Decisions:** the decision records it implements
- **Rules:** the files in `.claude/rules/` that apply
- **Depends on:** none | work order NNNN

## Goal

What exists when this is done, and why: one paragraph, linking the decision or the design session it comes from.

## Read first

- `path/to/file:12-80`: why it matters.

## Reuse

- The helpers, fixtures and patterns to use instead of writing new ones.

## Contract

Everything the rest of the system will rely on, spelled out: module paths, signatures and types, data structures, schemas, routes with their status codes, and events.

Alternatively: the stubs already in `path` are the contract. Make them real without changing their signatures.

## Behavior

1. A rule the code must enforce, including its edge cases and failure modes. Every rule is testable.

## Acceptance tests

| Test | Proves | Written by |
|---|---|---|
| `path/to/test::test_rejects_y` | Behavior 1 | implementer, or lead (don't modify) |

## Gates

The commands that must pass, if they differ from those in `.claude/working-model.json`.

## Out of scope

- What not to do or touch, even if it looks related.

## Stop and report BLOCKED if

- the order contradicts a decision, a rule or the code;
- you need a decision this order doesn't make, such as a name, a type, a status code, a dependency, or a file outside the contract;
- the contract can't be met without touching files outside the order's scope.

## Outcome

The lead fills this in when the order closes: the review verdict, amendments made during implementation, and follow-ups. The commit names this order in its body (`Work order: NNNN`).
