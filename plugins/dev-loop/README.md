# dev-loop Claude plugin

Source of truth for skill text is `skills/` in the repo root. `plugins/dev-loop/skills/` is a packaging copy.

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

Plugin hooks call the installed CLI. Run `./dev-loop/install.sh` first.

Knobs: `~/.config/dev-conductor/dev-loop/config.yaml`.

## Loop agents (packaged here)

- `code-reviewer` — diff review (silent failures, test gaps, ML/eval holes, confidence ≥ 80)
- `debugger` — root cause on red verify
- `code-simplifier` — optional `stages.simplify`; off by default

`design-lead` is not part of this plugin; it lives with frontend-design in `~/dev/mac-ai-setup`.
