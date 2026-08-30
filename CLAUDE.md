# dev-conductor

Jira-to-PR loop and Claude/Cursor plugin. This is not a product application.

## Commands

- Loop tests: `python3 -m unittest discover -s dev-loop/tests -v`
- Enrich tests: `python3 -m unittest discover -s claude/prompt-enrich/tests -v`
- Eval (fake Jira): `python3 dev-loop/cli.py --config dev-loop/config.test.yaml eval --repo ~/dev/devloop-lab`
- Install: `./install.sh`

## Layout

- `dev-loop/` — conductor CLI, config, fake-jira, tests
- `plugins/dev-loop/` — Claude plugin wrapper (packaging copies)
- `skills/` — loop + prompt-enrich skills (source of truth)
- `claude/agents/` — `code-reviewer`, `debugger`, `code-simplifier`
- `claude/commands/dev-loop.md` — slash command
- `claude/prompt-enrich/` — grill + launch hooks (used by spec stage)
- `cursor/dev-loop/` — Cursor copies of loop skills/rules (do not edit `skills/` to “make Cursor work”)

## Conventions

- Config: `~/.config/dev-conductor/dev-loop/config.yaml`
- Secrets: `~/.config/dev-conductor/secrets.env` (never commit)
- Jira REST + `gh`, not Jira/GitHub MCP
- Handshake files in the run dir: `SPEC_APPROVED`, `SESSION_DONE`

Machine snapshot (SSH, homelab, OpenRouter, Cursor product files, path-scoped stack rules) lives in sibling `~/dev/mac-ai-setup`.
