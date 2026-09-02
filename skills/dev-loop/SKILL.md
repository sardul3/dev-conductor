---
name: dev-loop
description: Run the Jira-to-PR conductor for a ticket. Use when the user says /dev-loop, names a Jira key (ASE-12, LAB-1), says work this story/ticket, or asks to start the conductor from a repo under ~/dev. Do not use Jira MCP or GitHub MCP.
---

# Dev-loop

The CLI owns fetch, verify, ship, and Jira workflow events (`on_start` on `start` also assigns the current user). You own grilling, tests, implementation, and handshake files. Secrets: `ATLASSIAN_*` in `~/.config/dev-conductor/secrets.env`. Config: `~/.config/dev-conductor/dev-loop/config.yaml`.

```bash
CLI="dev-loop"   # ~/.local/bin/dev-loop → python3 ~/.claude/hooks/dev-loop/cli.py
# alias: dl
```

Never guess the repo. Never `continue --no-wait` (that runs every remaining stage with no agent). Never `finish-branch` — ship is `step` / `continue`. Never commit `main`/`master`.

Never paste CLI `--help`, argparse usage, or raw stderr into the user message. Parse JSON; ask with **AskQuestion**.

## 1. Ticket + repo

If the user omitted the Jira key and/or `--repo`, and cwd is not already a **git** repo under `~/dev` with a GitHub remote:

1. `$CLI keys --format json`. If `count` is 0, `$CLI keys --recent --format json` (sprint JQL is often empty).
2. `$CLI repos --format json` (`--format` may follow the subcommand).
3. **One** AskQuestion with two questions:
   - Ticket: each `tickets[].key` (option id = key). Cursor adds Other if they want to type a key.
   - Repo: each `candidates[].label` (option id = `path`) plus `__create__` labeled `create_label`. Prefer `kind: git`. Do **not** default to cwd when `kind` is `folder` or the directory is empty.
4. `__create__` → ask for a folder name → `$CLI init-repo NAME` → use printed `path`.
5. `kind: folder` (not `git`) → `$CLI init-repo` that name first so `.git` and the GitHub remote exist. Never `start` on an empty folder.
6. If the ticket summary/product name does not match the repo folder, AskQuestion before `start`.

Then `$CLI start KEY --repo PATH`. If cwd is already that **git** repo, `$CLI start KEY` is enough.

## 2. After start

**Cursor workspace (mandatory):** start/step print `dev-loop: workspace PATH` (also `workspace` on `$CLI progress KEY` / `$CLI status`). If that path is set, the **first** action is Cursor `cursor-app-control` `move_agent_to_root` with `rootPath` = that path. Inspect the schema via GetDynamicTools first. Do this before grilling or writing files. Isolation worktrees live at `{repo}-worktrees/{KEY}` next to the clone (no leading dot). The clone under `~/dev` is not the ticket workspace when isolation is worktree.

Grill in this chat (`story-spec`) with **AskQuestion** (recommended option first). On **user yes**, `$CLI approve KEY` (writes `SPEC_APPROVED` and steps once). Do not write four handshake files.

| Runtime | Command |
| ------- | ------- |
| Cursor (`runtime.agent: cursor`) | `$CLI step KEY` — one stage, return |
| Claude (`agent: claude`) | `$CLI continue KEY` — blocking loop |

**Cursor stages:** each `step` prints a prompt path. Do that work, write `STAGE_DONE` (and `SESSION_DONE`), then `step` again. Test-writer: Task a **new** Agent. `SPEC_APPROVED` is spec-only, not ticket-done.

Handshake dir: `~/.config/dev-conductor/dev-loop/runs/KEY/`. Check `$CLI progress KEY` if lost. `step`/`approve`/`start` write the run dir; do not run them in a sandbox that cannot write `~/.config/dev-conductor`.

## 3. Status while running

Agent-facing CLI is brief (`$CLI`, `keys`, `status`, `progress`). Caps (`STOPPED` in the run dir), worktrees, poller: [reference.md](reference.md).

## 4. GitHub PR body

CLI writes the PR (`gh pr create`). If you edit a live PR, match this shape. Never dump `spec.md`.

```
## Summary
1–3 sentences of what shipped (Jira summary / spec title). Not the full spec.

Jira: [KEY](https://<ATLASSIAN_BASE_URL>/browse/KEY)

## Test plan
Concrete commands from the inferred verify recipe for THIS repo (expect exit 0).

## Evidence
- Visual proof for **every** ticket. Text-only verify.log is not enough.
- UI: screen/flow screenshot or short recording.
- Backend/API/scaffold: terminal snapshots of the inferred commands (tests/build green, app up, curl / `python -m` / health). Names: `tests.png`, `run.png`, `curl.png`.
```

- **Jira** is always a markdown browse link. Never bare `Jira: KEY`.
- **No spec excerpt.** Reviewers open Jira / `spec.md`. Do not paste Given/When/Then.
- **Test plan** is real commands (`uv sync`, `uv run pytest`, lint/type/run if this repo has them) — not “run the project test command”.
- **Evidence** is mandatory for all tickets. After verify is green, **before** `step` ship, write 1–n images/videos to `~/.config/dev-conductor/dev-loop/runs/KEY/evidence/` (png/jpg/webp/gif/webm/mp4). Capture with the browser screenshot tool, macOS `screencapture`, or a PNG of the terminal — the CLI cannot screenshot itself. Ship attaches via `gh pr comment --attach`. Do not commit pngs into the product repo. If ship says visual evidence required, write the files and `step` again.
