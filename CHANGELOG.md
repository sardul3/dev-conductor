# Changelog

## 2026-09-02 — Cursor /dev-loop

### Picker and grill

- `dev-loop repos --format json` and `--format` after the subcommand both work
- `dev-loop keys --recent` when sprint JQL is empty
- Cursor AskQuestion for repo/ticket and spec grill (not markdown ❓)
- `dev-loop approve KEY` writes spec handshake and steps (no four touch files)
- Agents must not paste CLI `--help` into chat

### Worktrees and IDE

- Worktrees live at `{repo}-worktrees/{KEY}` (no hidden `.langchain-worktrees`)
- After start/step, print `dev-loop: workspace PATH` and switch the Cursor root there

### Tests and verify

- Test-writer: application seams only — no nested `uv run pytest`, ruff, or pyright as tests
- Infer prefers `uv run pytest` (and uv for ruff/pyright) in the leased worktree
- Python `.gitignore` so `__pycache__` is not staged

### Jira

- `workflow.enabled` defaults on
- `on_start`: In Progress + comment (no silent skip)
- Assign to the Jira user when unassigned
- `on_pr` comment includes the PR URL

### GitHub PRs

- Jira is a browse link, no spec dump
- Test plan is real commands
- Visual evidence required on every ship (backend: terminal snapshots in `runs/KEY/evidence/`)

### Docs

- cursor/README.md, /dev-loop command, AGENTS.md isolation path
