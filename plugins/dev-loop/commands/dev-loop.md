Run the Jira → spec → tests → TDD → verify → review → PR conductor.

Usage: `/dev-loop PROJ-123` optional `--repo /path`

If `--repo` is missing and cwd is not a git repo under `~/dev`, **do not guess**. Run:

```bash
python3 ~/.claude/hooks/dev-loop/cli.py repos
```

Then ask the user with a **dropdown**: each candidate path plus “Create a new folder/repo under ~/dev”. Never default to mac-ai-setup. After they pick:

```bash
python3 ~/.claude/hooks/dev-loop/cli.py start KEY --repo PATH
```

New project: `python3 ~/.claude/hooks/dev-loop/cli.py init-repo FOLDER-NAME` then start with that path.

If `$ARGUMENTS` is empty, ask for the Jira key. After spec approval (`SPEC_APPROVED` or `APPROVED` in the run dir). Check `progress.md` for which stage is current:

```bash
python3 ~/.claude/hooks/dev-loop/cli.py continue KEY --repo PATH
```

Requires GitHub remote, `gh` auth, and Atlassian secrets in `~/.config/dev-conductor/secrets.env`. No Jira/GitHub MCP.
