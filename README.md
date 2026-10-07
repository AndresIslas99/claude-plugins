# andres-plugins

A personal marketplace of Claude Code plugins.

| Plugin | What it does |
|---|---|
| [`wm`](plugins/wm/README.md) | A working model: Opus leads, decides and writes decided code behind a commit gate. Sonnet takes work orders when delegating pays, Opus reviews risky changes, Fable advises on the hardest problems with the user's approval, and Haiku searches. Hooks enforce each project's gates and every agent's limits. |

Install it from GitHub, or from a local clone:

```bash
claude plugin marketplace add AndresIslas99/claude-plugins   # or the path of a clone
claude plugin install wm@andres-plugins
```

`just test` runs every plugin's hook tests, `just validate` checks the manifests, and `just eval` runs wm's eval cases in real sessions.

## License

[MIT](LICENSE).
