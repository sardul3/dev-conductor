# dev-conductor

Jira-to-PR loop and Claude/Cursor plugin.

## Commands

- Loop tests: `python3 -m unittest discover -s dev-loop/tests -v`
- Enrich tests: `python3 -m unittest discover -s claude/prompt-enrich/tests -v`
- Eval: `python3 dev-loop/cli.py --config dev-loop/config.test.yaml eval --repo <lab-repo>`
- Install: `./install.sh`

## Layout

- `dev-loop/` — CLI, config, fake-jira, tests
- `plugins/dev-loop/` — plugin wrapper (symlinks to `skills/` and `claude/`)
- `skills/` — loop + prompt-enrich skills
- `claude/agents/` — `code-reviewer`, `debugger`, `code-simplifier`
- `claude/commands/dev-loop.md` — slash command
- `claude/prompt-enrich/` — grill + launch
- `cursor/dev-loop/` — Cursor install + `dev-loop.mdc`

## Conventions

- Config: `~/.config/dev-conductor/dev-loop/config.yaml`
- Secrets: `~/.config/dev-conductor/secrets.env` (never commit)
- Jira REST + `gh`, not Jira/GitHub MCP
- Handshake files in the run dir: `SPEC_APPROVED`, `SESSION_DONE`
