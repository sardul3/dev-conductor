# Project notes for agents

dev-conductor is the Jira-to-PR loop. Do not silently revert these:

- Jira REST + `gh`, not Jira or GitHub MCP. Tickets stay the source of requirements.
- Handshake files in the run dir: `SPEC_APPROVED`, `SESSION_DONE`. `SPEC_APPROVED` means the spec is accepted, not that the ticket is done.
- Isolation: `git.isolation: treehouse` + `queue.max_active: 3`. Eval (`config.test.yaml`) uses `isolation: none`.
- Secrets stay in `~/.config/dev-conductor/secrets.env`. Never commit them.
- Procedures live in `skills/`. Stack law lives in path-scoped rules. Do not paste those bodies here.

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
- `.envfiles/` — canonical `AGENTS.md` / `CLAUDE.md` (this file). Root pointers load it.

## Working agreements

- Never auto-add an agent name as a commit co-author.
- Before using a harness feature that immediately spawns a large swarm of subagents, explain the tradeoff and ask.

## Maintaining this file

Keep this file for knowledge useful to almost every future agent session in this project.
Do not repeat what the codebase already shows; point to the authoritative file or command instead.
Prefer rewriting or pruning existing entries over appending new ones.
When updating this file, preserve this bar for all agents and keep entries concise.
