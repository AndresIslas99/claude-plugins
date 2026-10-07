---
name: adopt
description: Set up the wm working model in the current project, or upgrade an adopted one. Inspects the project, then creates with the user its CLAUDE.md working-model section, .claude/working-model.json (gates and lead-owned files), path-scoped rules from its existing decisions, the work-order and consult directories, and the project settings. Use it when starting a new project, or when the session's reminder says this project hasn't adopted the working model.
argument-hint: "[upgrade]"
disable-model-invocation: true
---

# Adopt the working model

Templates for this skill: !`echo "${CLAUDE_SKILL_DIR}/templates"`

The project's current configuration:

!`cat "${CLAUDE_PROJECT_DIR}/.claude/working-model.json" 2>/dev/null || echo "None yet: this is a first adoption."`

You are the lead, setting up the project's layer of the working model with the user. The plugin provides the agents, the skills and the hooks. The project provides what only it can say: its gates, its lead-owned files, its decisions and its rules. If the project already has a configuration, this is an upgrade: jump to the last section.

## 1. Inspect

Use `wm:scout` for the sweep, and read the key files yourself:
- the README, `CLAUDE.md`, and any docs or decision records (ADRs);
- the build and test commands, from justfile, Makefile, package.json scripts, pyproject.toml, Cargo.toml, go.mod, and the CI workflows;
- existing linters, type checkers, formatters, and their configuration;
- the existing `.claude/` directory, if any.

A project that ships its own copy of the working model (`.claude/hooks/agent_gate.py`) needs a decision first: migrate it to the plugin, or keep its copy and disable the plugin there.

## 2. Propose, then decide with the user

Present the proposal and use AskUserQuestion for the real choices:

- **Gates:** the commands that prove the code is correct, each with the globs of the files it covers (`when`). Prefer the commands CI runs. Put the fast static checks in `gates` and the slow ones in `tests`, which run only after the gates pass.
- **Lead-owned files:** dependency manifests, tool and gate configuration, CI workflows, deployment and secrets. `CLAUDE.md`, `.claude/`, lockfiles, `.env` files and the three directories below are lead-owned already.
- **Directories:** work orders, consults and decision records. The defaults are `docs/work-orders`, `docs/consults` and `docs/adr`; set `decisions` to null if the project keeps no decision records. If it keeps none, offer to start them.
- **Protected branches:** those that deploy or that nobody commits to directly.
- **Commits:** whether the lead commits each approved work order, or only proposes the commit.
- **Destructive commands** specific to this project (database resets, VM rebuilds), to add to `denyCommands`.

## 3. Write

- `.claude/working-model.json`, from `working-model.json` in the templates.
- `CLAUDE.md`: add the section from `claude-md-section.md` and fill in its placeholders. If there is no `CLAUDE.md`, write one first: what the project is, where its decisions live, and its everyday commands. Keep everything that's already there.
- `.claude/rules/`: one file per area, scoped with `paths:`. Summarize only what the project has already decided (decision records, documented conventions, tool configuration), and cite the source of each rule. In a new project with nothing decided, write none, and propose a `/wm:design-session` for its first decisions instead.
- The work orders directory, with `README.md` and `template.md` from `work-orders-readme.md` and `work-order.md`. Do the same for the consults directory, with `consults-readme.md` and `consult.md`.
- If the project keeps decision records, write one from `decision-record.md` that records the adoption. Its status is `Proposed` until the user accepts it.
- `.claude/settings.json`: merge in what `settings.json` in the templates holds, and keep everything already there.

## 4. Verify and hand over

- Run each gate once, and fix the configuration until every gate passes on the clean tree.
- Check that the agents load: ask `wm:scout` where the project's entry point is.
- Tell the user what changed, and propose a commit on a topic branch. The rules and the configuration are lead-owned and versioned with the project.

## Upgrade

Compare the project's work-order and consult templates and its configuration with this skill's templates. Then show the user the differences, and apply what they approve. Never touch the project's rules or decisions while upgrading.
