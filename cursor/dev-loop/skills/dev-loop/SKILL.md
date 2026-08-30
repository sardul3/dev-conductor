---
name: dev-loop
description: Start the Jira-to-PR developer loop for a ticket. Use when the user says /dev-loop, work this Jira story, or run the conductor from a repo under ~/dev.
---

# Dev-loop

Run the conductor. Do not use Jira MCP or GitHub MCP. Knobs live in `~/.config/dev-conductor/dev-loop/config.yaml`. Real Jira needs `ATLASSIAN_BASE_URL`, `ATLASSIAN_EMAIL`, `ATLASSIAN_API_TOKEN` in `~/.config/dev-conductor/secrets.env`.

## Repo (do not guess)

If the user did not pass `--repo` and the current directory is not a git repo under `~/dev`:

1. Run `python3 ~/.claude/hooks/dev-loop/cli.py repos` and read the JSON.
2. **Ask the user with a dropdown** (Cursor: AskQuestion). Options: every `candidates[].label` (id = `path`) plus one extra option id `__create__` labeled with `create_label`.
3. Never pick `mac-ai-setup` or any other folder unless the user selected it.
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
python3 ~/.claude/hooks/dev-loop/cli.py progress KEY
```

`progress.md` / `status.json` in the run dir name the current **stage** (fetch, spec, test_writer, writer, verify, review, ship). `SPEC_APPROVED` is spec-only. `SESSION_DONE` means that agent session finished.

Unattended e2e (no spec gate): `autonomy.profile: unattended` in config.yaml. Still pass `--repo`. Merge stays `alert` unless `autonomy.merge: auto`.

Poller: `cli.py poll` / `install-poller`. Never commit `main`/`master`.

## Cursor

Claude slash `/dev-loop` and SessionStart hooks do not run here. Same CLI: `python3 ~/.claude/hooks/dev-loop/cli.py`. Use AskQuestion for the repo dropdown. Do not edit `skills/` in the repo; this tree is the Cursor copy.
