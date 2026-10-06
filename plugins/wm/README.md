# wm: a working model for Claude Code

The `wm` plugin splits work between models, so decisions get the strongest reasoning and code is written at the lowest cost that keeps its quality. Hooks enforce it, because a rule that isn't checked automatically erodes. It first ran as project files in freight-crm (its ADR 0033); this plugin is the reusable version.

| Role | Model | Does |
|---|---|---|
| Lead: the main session | Opus | Talks with the user, decides, writes decisions, rules and work orders, reviews and commits |
| `wm:implementer` | Sonnet | Carries out one work order: tests first, code, green gates, a fixed-format report |
| `wm:reviewer` | Opus | Reviews a diff against its work order, the rules and the decisions |
| `wm:fable-advisor` | Fable | Decision memos on problems of extreme complexity; the user approves every call |
| `wm:scout` | Haiku | Codebase searches, answered with `path:line` pointers |
| `wm:researcher` | Sonnet | Web research with dated sources |

The skills:
- `/wm:implement` routes a request by tier (T0 to T4) and runs a work order through the implementer, the gates, the review and the commit.
- `/wm:design-session` makes and records a new decision with the user.
- `/wm:ask-fable` consults the advisor through a dossier.
- `/wm:adopt` sets the model up in a project, or upgrades it.

## Install

```bash
claude plugin marketplace add ~/Documents/Personal/Code/claude-plugins
claude plugin install wm@andres-plugins
```

Enabled at user scope, the plugin applies to every project:
- every session starts with the model's essentials;
- Explore searches are redirected to `wm:scout`;
- Fable calls ask the user first.

A project gets the full workflow, with work orders, rules and enforced gates, once it runs `/wm:adopt`.

## What the hooks enforce

| Hook | Enforces |
|---|---|
| `SessionStart` → `session_context.py` | Puts the model's essentials into every session; in a project that hasn't adopted it, also offers `/wm:adopt` |
| `PreToolUse` on `Agent` → `agent_gate.py` | Explore runs only on a cheap model, otherwise searches go to `wm:scout`; every Fable call asks the user |
| `PreToolUse` on `Bash`, `Edit`, `Write` → `subagent_guard.py` | wm agents can't change git history, dependencies, secrets, remote systems or lead-owned files; the reviewer, the scout and the researcher write nothing, and the advisor writes only in the consults directory |
| `PreToolUse` on `SubagentHandback`, and `SubagentStop` → `done_gate.py` | `wm:implementer` can't report DONE while the project's gates fail for the changed files, or with new gate suppressions |

The guards act only on the wm agents, which they identify by the `agent_type` in the hook's input. The main session and other agents pass untouched. A project that ships its own copy of the model's hooks (`.claude/hooks/agent_gate.py`) is left alone.

## Project configuration: `.claude/working-model.json`

```json
{
  "version": 1,
  "gates": [{ "run": "just lint", "when": ["backend/**"] }],
  "tests": [{ "run": "just test", "when": ["backend/**"], "timeout": 900 }],
  "leadOwned": ["backend/pyproject.toml", ".github/"],
  "denyCommands": [{ "pattern": "\\bjust\\s+db-reset\\b", "reason": "Destroys the development data." }],
  "paths": { "workOrders": "docs/work-orders", "consults": "docs/consults", "decisions": "docs/adr" },
  "protectedBranches": ["main"]
}
```

- **`gates`**: fast checks. Each one runs in the repository root when a changed file matches one of its `when` globs; an entry with no `when` always runs.
- **`tests`**: slow checks, run only after every gate passes. `timeout` is in seconds and defaults to 600.
- **`leadOwned`**: paths only the lead edits, on top of `CLAUDE.md`, `.claude/`, lockfiles, `.env` files and the three `paths` directories. A path ending in `/` covers a directory, and globs work too.
- **`denyCommands`**: regular expressions for shell commands the wm agents may never run in this project.
- Globs use gitignore-style `**`, relative to the repository root. Without the file, nothing is known about the gates, so the done-gate checks only the report format and the suppressions.

## Why it looks like this

Measured on 2026-10-06, with Claude Code 2.1.292:

- **Plugin agents ignore their own frontmatter hooks**, as the documentation says. That's why every hook is declared in `hooks/hooks.json`.
- **Subagents end by calling the `SubagentHandback` tool.** A `Stop` or `SubagentStop` block arriving after it is discarded, so the done-gate denies the handback itself in `PreToolUse`.
- **Fable's approval needs the hook, not just a rule.** A `permissions.ask` rule didn't stop a headless session in auto mode, because the classifier answered; the hook's `ask` did.
- **The built-in Explore agent runs on the session's model**, Opus, even with `CLAUDE_CODE_SUBAGENT_MODEL` set.
- **A subagent costs about 20K tokens to start**, and prompt caches are per model.
- **Precedence differs for skills and agents.** A user-level skill shadows a project skill with the same name, while a project agent shadows a user-level agent. The plugin's names are namespaced (`wm:`), so they never collide.
- **Frontmatter hooks apply only to subagents.** An agent's hooks don't run when it's the main session (`claude --agent`).
- **The hooks run on the system `python3`**, which is 3.9 on macOS, so they avoid newer syntax.

## Test

```bash
just test
```

The tests build throwaway git repositories, so they don't depend on any project. Bump `version` in `.claude-plugin/plugin.json` and in the marketplace entry with every change, then refresh the installed copy:

```bash
claude plugin marketplace update andres-plugins
claude plugin update wm@andres-plugins
```
