# Cursor port

`./cursor/dev-loop/install.sh` copies the CLI to `~/.claude/hooks/dev-loop/`, **all** `skills/` into `~/.cursor/skills` and `~/.agents/skills`, Cursor `.mdc` rules, and user hooks (`sessionStart`, `beforeReadFile`).

```bash
./cursor/dev-loop/install.sh
```

Set `runtime.agent: cursor`. Drive the loop with `cli.py start` then `cli.py step` (never polls).
