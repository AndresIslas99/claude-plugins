# andres-plugins

A personal marketplace of Claude Code plugins.

| Plugin | What it does |
|---|---|
| [`wm`](plugins/wm/README.md) | A working model: Opus leads and decides, Sonnet implements precise work orders, Opus reviews, Fable advises on the hardest problems with the user's approval, and Haiku searches. Hooks enforce each project's gates and every agent's limits. |

Install it on this machine:

```bash
claude plugin marketplace add ~/Documents/Personal/Code/claude-plugins
claude plugin install wm@andres-plugins
```

Run every plugin's tests with `just test`.
