---
name: implement
description: Deliver a decided change with the wm working model - triage, the work done inline with tests first under the project's gates (or a work order for the Sonnet implementer when delegating pays), an Opus review for risky changes, rule updates, and one commit per approved change, which the commit gate checks. Use it whenever the user asks to implement, build, add, fix, refactor or test something in a project that has adopted the working model, or names a work order to resume.
argument-hint: "<what to implement, or a work order number to resume>"
---

# Implement: $ARGUMENTS

This project's configuration (`.claude/working-model.json`):

!`cat "${CLAUDE_PROJECT_DIR}/.claude/working-model.json" 2>/dev/null || echo "None: this project hasn't adopted the working model. Offer /wm:adopt. Until then, work from a precise brief and run the project's checks yourself."`

You are the lead: you decide, write the code for decided work, and verify. Below, "the gates" means the configuration's `gates` and `tests` that cover the changed files, and "work orders" means its `paths.workOrders` directory. If the request names an existing work order, resume it from its status (section 4).

## 1. Triage

| Tier | Signals | Route |
|---|---|---|
| T0 | A few lines in one or two files, and no design choice | Do it yourself, run the relevant gates, and commit only if the user asks |
| T1 | Decided behavior, one layer, an existing pattern to follow | Do it yourself, inline (section 2) |
| T2 | Several files or layers, a new public contract, or security-adjacent code; well specified and verifiable | Do it yourself, inline, with tests first, and with a review when it's risky (section 2). Delegate it (section 4) only when section 3 says it pays |
| T3 | Needs a decision the project hasn't made | Stop and run `/wm:design-session` first |
| T4 | Security-critical design, tenant isolation, concurrency or data integrity, an irreversible data-model choice, or real-time systems | Work it yourself at xhigh effort, with the user: ask them to run `/effort xhigh`, which keeps the cache, unlike a model change. Run `/wm:ask-fable` only after two failed attempts at xhigh |

Large isn't the same as hard. Announce the tier you chose, so the user can change it. Once a task has moved up a tier, it doesn't move back down.

**Escalation.** When an attempt fails, go up one step at a time, carrying the failure's evidence:
1. Retry once.
2. Raise the effort.
3. Work it at xhigh.
4. Only after two failed attempts at xhigh, consult Fable with `/wm:ask-fable`.

At this generation Opus 5.5 matches or beats Fable 5.1 on coding at about a fifth of the cost per solved task. To spend less, lower the effort rather than switching models.

## 2. Inline: T1 and T2

1. Read what the change needs: the decisions and rules that apply, and the code that will change. Send broad searches to `wm:scout`.
2. For T2, write the acceptance tests first, one or more per behavior rule, and run them to see each fail for the expected reason.
3. Make the smallest change that meets the decision. Match the surrounding code's idioms, naming and comment density, and reuse what's there.
4. Run the gates. Fix causes, not symptoms: never add a suppression to get green, unless you decide the suppression is right and say why in a comment.
5. Read your own diff (`git status`, `git diff`) against the request: every behavior rule has a test, nothing outside the scope changed, and nothing is left over from debugging.
6. For a risky T2 change, call `Agent` with `subagent_type: "wm:reviewer"` and the prompt `Review the uncommitted changes against this request: <the request and the rules that apply, in a few lines>.` Address its findings, or tell the user why you didn't. A change is risky when it touches:
   - authentication, authorization, secrets, or input at a trust boundary;
   - tenant isolation;
   - concurrency;
   - data integrity or migrations;
   - a new public contract that other code or users depend on.

   For any other T2 change, your own reading of the diff in step 5 is the review.
7. Close (section 5).

## 3. When delegating pays

In a pilot of 10 tasks with hidden tests, delegating every T2 task to the implementer cost about twice as much as plain Claude Code, for the same results, because writing and reviewing an order costs the lead more than the cheaper model saves. Delegate a T2 change only when one of these holds:
- **It would flood your context.** For example, a long mechanical change across many files, or a long loop of test runs you don't need to see.
- **It splits into independent parts** that can run in parallel, each in its own worktree.
- **The user wants the work order on record,** for example to hand the work to someone else.

## 4. Delegate: a work order for `wm:implementer`

**Prepare.**
- Make the lead-owned changes yourself, before the dispatch: dependencies (committed on their own), tool configuration and rules.
- When the contract is mostly types, as with a new module, interface or data structure, write it in code: signatures with docstrings, and bodies that raise "not implemented".
- For behavior that is critical to security or data integrity, write the acceptance tests yourself and mark them "lead" in the order. The implementer makes them pass and may not change them.

**Write the order.** Create `NNNN-short-title.md` in the work orders directory, with the next free number, from the `template.md` there, and give it the status `Ready`. The bar: an engineer with no access to this conversation can carry it out without making a single decision.
- Spell out every name, path, signature, type, schema, route, status code and event that other code will depend on.
- Number every behavior rule and give it at least one acceptance test. List the edge cases and failure modes instead of leaving them implied.
- In "Read first", give exact files and line ranges. In "Reuse", name the helpers, fixtures and patterns to use. In "Out of scope", say what not to touch.
- Before dispatching, check every factual claim in the order by reading or running it: line ranges, command output, current behavior. The implementer treats the order as the truth, so a wrong claim costs a round trip.

**Dispatch.**
- Call `Agent` with `subagent_type: "wm:implementer"` and a short prompt: `Carry out <path to the order>. Follow your protocol and end with your report.` Set the order to `In progress`.
- Dispatch through the Agent tool. An agent run as the main session (`claude --agent`) gets none of the plugin's checks.
- Effort: leave the agent's default, medium. Pass `effort: "high"` for intricate logic (concurrency, parsing, algorithms). Don't go below medium: at low effort Sonnet 5.5 sometimes skips the real check.
- Run one implementer at a time, except for orders that touch disjoint files, each with `isolation: "worktree"`. Never run in parallel an order that touches migrations, the composition root, dependency manifests or lockfiles.

**Verify.** The done-gate has run the gates on the implementer's changes, and its verdict reaches you after the report.
- **BLOCKED:** answer the questions yourself when the decisions and rules settle them, and ask the user otherwise. Amend the order and note the amendment in it, then continue the same implementer with `SendMessage`.
- **PARTIAL:** either fill the gap in the order and continue the same implementer, or finish the work yourself if what's left is small.
- **DONE:** read `git status` and `git diff --stat`, then call `Agent` with `subagent_type: "wm:reviewer"` and the prompt `Review the uncommitted changes against <path to the order>.` For the critical piece of a T4 decision, you may also run `/wm:ask-fable`; the user approves each call.
- **CHANGES_REQUESTED:** send the findings to the same implementer with `SendMessage`, and re-review only what changed. After two rounds that don't converge, stop delegating: fix it yourself.
- **A FAILING verdict:** don't accept the work as it is. Fix what the verdict lists, or hand it back with an amended order.

Then fill in the order's Outcome (the review verdict, the amendments, the follow-ups), set it to `Done`, and close (section 5).

## 5. Close

1. **Encode what you learned.** Turn each rule candidate from a review into a short rule in `.claude/rules/` that cites its source. Do the same for any mistake you had to correct that could happen again. Only the lead writes rules.
2. **Commit**, one commit per approved change, when the user has approved that practice for this project (its `CLAUDE.md` says so); otherwise propose the commit. Never push unless the user asks.
   - If you're on one of the configuration's `protectedBranches`, first create a topic branch for the work package.
   - Stage the change, its work order if there is one, and any rule updates, and nothing else.
   - Write a Conventional Commit whose first line has at most 72 characters. Put `Work order: NNNN` in the body when there is one.
   - The commit gate runs the gates again before the commit goes through, and denies it with their output if they fail. Fix the cause and commit again. If git hooks fail, fix the cause too; never use `--no-verify`.
3. **Report to the user:** what changed, the gates, the review verdict, the commit, and the follow-ups.
