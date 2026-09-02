---
name: dev-loop
description: Run the Jira-to-PR conductor for a ticket. Use when the user says /dev-loop, names a Jira key (ASE-12, LAB-1), says work this story/ticket, or asks to start the conductor from a repo under ~/dev. Do not use Jira MCP or GitHub MCP.
---

# Dev-loop

The CLI owns fetch, verify, and ship. You own grilling, tests, implementation, and handshake files. Secrets: `ATLASSIAN_*` in `~/.config/dev-conductor/secrets.env`. Config: `~/.config/dev-conductor/dev-loop/config.yaml`.

```bash
CLI="python3 ~/.claude/hooks/dev-loop/cli.py"
```

Never guess the repo. Never `continue --no-wait` (that runs every remaining stage with no agent). Never `finish-branch` — ship is `step` / `continue`. Never commit `main`/`master`.

## 1. Repo

If the user did not pass `--repo` and cwd is not the git repo under `~/dev`:

1. `$CLI repos --format json`
2. AskQuestion dropdown: each `candidates[].label` (id = `path`) plus `__create__` labeled `create_label`.
3. `__create__` → ask for a folder name → `$CLI init-repo NAME` → use printed path.
4. `folder` (not `git`) → prefer `init-repo` so the GitHub remote exists.

Then `$CLI start KEY --repo PATH`. If cwd is already that repo, `$CLI start KEY` is enough.

## 2. After start

Grill in this chat (`story-spec`). On **user yes**, write `SPEC_APPROVED` then:

| Runtime | Command |
| ------- | ------- |
| Cursor (`runtime.agent: cursor`) | `$CLI step KEY` — one stage, return |
| Claude (`agent: claude`) | `$CLI continue KEY` — blocking loop |

**Cursor stages:** each `step` prints a prompt path. Do that work, write `STAGE_DONE` (and `SESSION_DONE`), then `step` again. Test-writer: Task a **new** Agent. `SPEC_APPROVED` is spec-only, not ticket-done.

Handshake dir: `~/.config/dev-conductor/dev-loop/runs/KEY/`. Check `$CLI progress KEY` if lost.

## 3. Status while running

Agent-facing CLI is brief (`$CLI`, `keys`, `status`, `progress`). Caps (`STOPPED` in the run dir), worktrees, poller: [reference.md](reference.md).
