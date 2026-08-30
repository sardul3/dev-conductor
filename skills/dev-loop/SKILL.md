---
name: dev-loop
description: Start the Jira-to-PR developer loop for a ticket. Use when the user says /dev-loop, work this Jira story, or run the conductor from a repo under ~/dev.
---

# Dev-loop

Run the conductor. Do not use Jira MCP or GitHub MCP. Knobs live in `~/.config/dev-conductor/dev-loop/config.yaml`. Real Jira needs `ATLASSIAN_BASE_URL`, `ATLASSIAN_EMAIL`, `ATLASSIAN_API_TOKEN` in `~/.config/dev-conductor/secrets.env`.

## Repo (do not guess)

If the user did not pass `--repo` and the current directory is not a git repo under `~/dev`:

1. Run `python3 ~/.claude/hooks/dev-loop/cli.py repos --format json` and read the JSON.
2. **Ask the user with a dropdown** (Cursor: AskQuestion). Options: every `candidates[].label` (id = `path`) plus one extra option id `__create__` labeled with `create_label`.
3. Never pick a folder unless the user selected it.
4. If they choose `__create__`, ask for a folder name, then:
   `python3 ~/.claude/hooks/dev-loop/cli.py init-repo NAME`
   Use the printed path as `--repo`.
5. If they choose a `folder` (not `git`), `init-repo` that name or `start` will git-init it. Prefer `init-repo` so GitHub remote is created.
6. Then:
   `python3 ~/.claude/hooks/dev-loop/cli.py start KEY --repo PATH`

If cwd is already the right git repo, `start KEY` without `--repo` is fine.

```bash
python3 ~/.claude/hooks/dev-loop/cli.py start KEY [--repo PATH]
python3 ~/.claude/hooks/dev-loop/cli.py continue KEY
```

Poller: `cli.py poll` / `install-poller`. Never commit `main`/`master`.
Agent reads use brief output (`cli.py` with no args, `keys`, `status`, `progress`). Picker JSON is `--format json`. New connector: `brief.Connector` + `fetch()`.

Long-run caps (`caps.max_launches` / `max_tokens` / `max_budget_usd` / `wall_sec`, 0 = off) stop further agent launches and write `STOPPED` in the run dir. Unattended still needs these set; they do not default on. Parallelism is `queue.max_active` (treehouse leases), not tmux fan-out.

Isolation: example config uses `git.isolation: treehouse` (leased worktree) and `queue.max_active: 3`. Start from the clone under `~/dev`; do not `cd` into `~/.treehouse` yourself. A fourth in-progress ticket exits until one ships or you `treehouse return PATH`.
