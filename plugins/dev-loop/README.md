# dev-loop Claude plugin

`agents/`, `commands/`, and `skills/` are **symlinks** to `claude/agents`, `claude/commands`, and repo-root `skills/`. Edit the sources, not a second copy.

## Install (this Mac)

```bash
./install.sh
# or just: ./dev-loop/install.sh
```

That copies the CLI to `~/.claude/hooks/dev-loop/`, merges SessionStart/PreToolUse, and installs skills.

## Marketplace / plugin

```bash
claude plugin marketplace add /path/to/dev-conductor
```

Install from a git clone so the symlinks resolve. Plugin hooks call the installed CLI. Run `./dev-loop/install.sh` first.

Knobs: `~/.config/dev-conductor/dev-loop/config.yaml`.

## Loop agents

- `code-reviewer` — diff review (silent failures, test gaps, ML/eval holes, confidence ≥ 80)
- `debugger` — root cause on red verify
- `code-simplifier` — optional `stages.simplify`; off by default
