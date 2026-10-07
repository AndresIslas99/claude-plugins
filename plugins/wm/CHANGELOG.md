# Changelog

## 2.2.0 (2026-10-07)

- **The lead writes decided code itself.** `/wm:implement` does T2 work inline, with tests first and the gates, and adds a `wm:reviewer` review only for risky changes: authentication, authorization, secrets, tenant isolation, concurrency, data integrity, migrations or a new public contract. It goes to `wm:implementer` only when the change would flood the lead's context, splits into parallel parts, or the user wants the work order on record. Measured in two pilots: delegating every T2 task cost about twice as much as plain Claude Code, and reviewing every inline T2 change still cost 1.76 times as much, for the same results.
- **The lead can't commit while the project's checks fail.** A new hook, `commit_gate.py`, runs the gates and then the tests on the lead's `git commit`, and denies it with their output if they fail.
- The reviewer reviews a request as well as a work order, and the done-gate and the commit gate share their check runner (`wm_checks.py`).

## 2.1.0 (2026-10-07)

- **The done-gate catches commits the guard can't see.** If HEAD moved while the implementer worked, for example through a commit a script made, that is an integrity failure.
- **The gate hands an unfixable failure to the lead at once.** When the implementer reports BLOCKED or PARTIAL on the failures it was just sent back for, such as a lead-owned file a formatter rewrote, the gate ends with a FAILING verdict instead of sending it back again. The gate no longer tells the implementer to revert lead-owned files, which its limits forbid.
- **A hung git can't open the gates.** Each git call gives up after 20 seconds (`WM_GIT_TIMEOUT`), so the hook applies its own failure policy instead of reaching Claude Code's timeout, which lets the action through.
- `/wm:doctor` checks that git answers and is recent enough.
- The verdict counts one changed file in the singular, and a FAILING verdict no longer claims it used every retry.
- The evals now prove the mechanisms rather than the model's good behavior. A docs formatter that rewrites CLAUDE.md as a side effect checks the diff-based integrity check. The verdict case checks that the gate runs the project's own lint, even when the work order named another check.

## 2.0.1 (2026-10-07)

- The lead gets the gate's verdict in every permission mode. The Agent gate runs `wm:implementer` in the foreground unless it has its own worktree, because a background launch fires `PostToolUse` before the implementer runs.
- The verdict lists the times the implementer was sent back, with the reasons.
- The cost per agent is summed from the subagent's transcript, because the response's `usage` covers only its last message.

## 2.0.0 (2026-10-07)

- **The done-gate checks the implementer's own diff**, from a snapshot taken at `SubagentStart`. It catches lead-owned files changed by any tool, new suppressions and weakened check configuration, and passes deleted tests and removed assertions to the lead as warnings.
- **The gate runs within a time budget, and it converges** when its own checks break.
- **The lead gets a verdict after every implementer run**, and every subagent's model is audited against its role's.
- **`launch.sh` applies each hook's failure policy:** the gates fail closed, the rest fail open and leave receipts.
- **Agent routing:**
  - wm agents can't start agents;
  - Fable consults are capped per session;
  - `models` in the project configuration, or `WM_MODELS` for the machine, reroute an agent.
- **`/wm:doctor`**, the eval suite, and CI on Python 3.9 and 3.14.
- **Routing recalibrated to measured evidence:**
  - T1 is done inline;
  - the implementer runs at medium effort and stays within its order;
  - Fable is consulted only after two failed attempts at xhigh.

## 1.0.1 (2026-10-06)

- The guard lets `git stash list` and `git stash show` through, as the implementer reported in its first live run.

## 1.0.0 (2026-10-06)

- The first release: the roles, the four skills, the hooks, and `/wm:adopt`.
