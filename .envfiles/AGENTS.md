# Project notes for agents

dev-conductor is the Jira-to-PR loop. Do not silently revert these:

- Jira REST + `gh`, not Jira or GitHub MCP. Tickets stay the source of requirements.
- Handshake files in the run dir: `SPEC_APPROVED`, `SESSION_DONE`. `SPEC_APPROVED` means the spec is accepted, not that the ticket is done.
- Isolation: `git.isolation: worktree` (default; native git worktree) + `queue.max_active: 3`. `treehouse` remains opt-in. Eval (`config.test.yaml`) uses `isolation: none`.
- Secrets stay in `~/.config/dev-conductor/secrets.env`. Never commit them.
- Procedures live in `skills/`. Stack law lives in `.envfiles/rules/` (path-scoped). Do not paste those bodies here.
- Agent memory: review writes `verdict.json` `metadata[]`; harness applies when `agent_memory.auto_apply` (default true). Skill `agent-memory` + `cli.py agent-memory`.
- Agent I/O is `brief/` (clip, 3–4 columns, count, empty, help[]). New connector: subclass `brief.Connector`, implement `fetch()`. Disk files stay JSON. Not AXI-branded.

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
- `.envfiles/` — canonical `AGENTS.md` / `CLAUDE.md` (this file) and path-scoped `rules/`. Root pointers load this file.

## Definition of done

The loop already is the pipeline. Do not add a second checklist in chat.

- Proof: `verify-before-done` (fresh test/build this turn). Quality gates are config (`quality.*`, `evidence`).
- UI: `lavish.enabled` (default `auto` = UI repos only). Not a ship blocker.
- Docs: `domain-glossary` only for a new term or a hard-to-reverse decision (`docs/adr/`). README only if install/usage/public API would be wrong. No empty ADRs.
- Review: spawned `code-reviewer` → `verdict.json`, then `gh pr`.
- Long runs: `caps.max_launches` / `max_tokens` / `max_budget_usd` / `wall_sec` (0 = off). Stop writes `STOPPED` in the run dir; not a second overnight product.

## Working agreements

- Never auto-add an agent name as a commit co-author.
- Before using a harness feature that immediately spawns a large swarm of subagents, explain the tradeoff and ask.

## Maintaining this file

Keep this file for knowledge useful to almost every future agent session in this project.
Do not repeat what the codebase already shows; point to the authoritative file or command instead.
Prefer rewriting or pruning existing entries over appending new ones.
When updating this file, preserve this bar for all agents and keep entries concise.
