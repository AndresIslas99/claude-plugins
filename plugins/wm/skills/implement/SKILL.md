---
name: implement
description: Deliver a decided change with the wm working model - triage, a work order, the Sonnet implementer, the project's gates, an Opus review, rule updates, and one commit per approved work order. Use it whenever the user asks to implement, build, add, fix, refactor or test something in a project that has adopted the working model, or names a work order to resume.
argument-hint: "<what to implement, or a work order number to resume>"
---

# Implement: $ARGUMENTS

This project's configuration (`.claude/working-model.json`):

!`cat "${CLAUDE_PROJECT_DIR}/.claude/working-model.json" 2>/dev/null || echo "None: this project hasn't adopted the working model. Offer /wm:adopt. Until then, work from a precise brief and run the project's checks yourself."`

You are the lead: you decide and verify, and `wm:implementer` writes the code. Below, "the gates" means the configuration's `gates` and `tests` that cover the changed files, and "work orders" means its `paths.workOrders` directory. If the request names an existing work order, resume it from its status.

## 1. Triage

| Tier | Signals | Route |
|---|---|---|
| T0 | A few lines in one or two files, and no design choice; an order would cost more than the change | Do it yourself, run the relevant gates, and commit only if the user asks |
| T1 | Decided behavior, one layer, an existing pattern to follow | Work order → implementer → you read the diff |
| T2 | Several files or layers, a new public contract, or security-adjacent code | Work order → implementer → `wm:reviewer` |
| T3 | Needs a decision the project hasn't made | Stop and run `/wm:design-session` first |
| T4 | Security-critical design, tenant isolation, concurrency or data integrity, an irreversible data-model choice, real-time systems, or two failed attempts | Stop and run `/wm:ask-fable` first |

Large isn't the same as hard. Split a large, clear change into several T1 or T2 orders instead of escalating it.

## 2. Prepare

- Read only what you need to write a precise order: the decisions and rules that apply, and the code that will change. Send broad searches to `wm:scout`.
- Make the lead-owned changes yourself, before the dispatch: dependencies (committed on their own), tool configuration and rules.
- When the contract is mostly types, as with a new module, interface or data structure, write it in code: signatures with docstrings, and bodies that raise "not implemented". Type-checked stubs are a more precise contract than prose.
- For behavior that is critical to security or data integrity, write the acceptance tests yourself and mark them "lead" in the order. The implementer makes them pass and may not change them.

## 3. Write the work order

Create `NNNN-short-title.md` in the work orders directory, with the next free number, from the `template.md` there, and give it the status `Ready`. The bar: an engineer with no access to this conversation can carry it out without making a single decision.

- Spell out every name, path, signature, type, schema, route, status code and event that other code will depend on.
- Number every behavior rule and give it at least one acceptance test. List the edge cases and failure modes instead of leaving them implied.
- In "Read first", give exact files and line ranges. In "Reuse", name the helpers, fixtures and patterns to use.
- In "Out of scope", say what not to touch.
- Before dispatching, check every factual claim in the order by reading or running it: line ranges, command output, current behavior. The implementer treats the order as the truth, so a wrong claim costs a round trip.

## 4. Dispatch

- Call `Agent` with `subagent_type: "wm:implementer"` and a short prompt: `Carry out <path to the order>. Follow your protocol and end with your report.` The order carries everything else. Set the order to `In progress`.
- Dispatch through the Agent tool. An agent run as the main session (`claude --agent`) gets none of the plugin's checks.
- Effort: leave the agent's default, high. Pass `effort: "medium"` for mechanical orders (renames, boilerplate, documentation), and `effort: "xhigh"` for intricate logic (concurrency, parsing, algorithms).
- Run one implementer at a time. Run orders in parallel only when they touch disjoint files, each with `isolation: "worktree"`. Never run in parallel an order that touches migrations, the composition root, dependency manifests or lockfiles.

## 5. Verify

- **BLOCKED:** answer the questions yourself when the decisions and rules settle them, and ask the user otherwise. Amend the order and note the amendment in it, then continue the same implementer with `SendMessage`.
- **PARTIAL:** read the failure. Either fill the gap in the order and continue the same implementer, or finish the work yourself if what's left is small.
- **DONE:** the done-gate hook has run the gates for the changed files. Read `git status` and `git diff --stat`, then review:
  - T1: read the diff yourself, against the order.
  - T2, and anything built on a T4 decision: call `Agent` with `subagent_type: "wm:reviewer"` and the prompt `Review the uncommitted changes against <path to the order>.`
  - For the critical piece of a T4 decision, you may also run `/wm:ask-fable` to have the advisor review it; the user approves each call.
- **CHANGES_REQUESTED:** send the findings to the same implementer with `SendMessage`, and re-review only what changed. After two rounds that don't converge, stop delegating: fix it yourself or rewrite the order.

## 6. Close

1. **Encode what you learned.** Turn each rule candidate from the review into a short rule in `.claude/rules/` that cites its source. Do the same for any mistake you had to correct yourself that could happen again. Only the lead writes rules.
2. **Run the gates once more**, for everything that changed. Hooks can fail silently, and you commit what you verified.
3. **Close the order.** Fill in its Outcome (the review verdict, the amendments, the follow-ups) and set its status to `Done`.
4. **Commit**, one commit per approved work order, when the user has approved that practice for this project (its `CLAUDE.md` says so); otherwise propose the commit. Never push unless the user asks.
   - If you're on one of the configuration's `protectedBranches`, first create a topic branch for the work package.
   - Stage the change, its work order and any rule updates, and nothing else.
   - Write a Conventional Commit whose first line has at most 72 characters, and put `Work order: NNNN` in the body.
   - If git hooks fail, fix the cause and commit again; never use `--no-verify`.
5. **Report to the user:** what changed, the gates, the review verdict, the commit, and the follow-ups.
