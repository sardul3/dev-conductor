Run the Jira → spec → tests → TDD → verify → review → PR conductor.

Usage: `/dev-loop PROJ-123` optional `--repo /path`

If `--repo` is missing and cwd is not a git repo under `~/dev`, **do not guess**. Run:

```bash
dev-loop repos
# or: python3 ~/.claude/hooks/dev-loop/cli.py repos
```

Then ask the user with a **dropdown**: each candidate path plus “Create a new folder/repo”. Do not guess a repo. After they pick:

```bash
dev-loop start KEY --repo PATH
```

New project: `dev-loop init-repo FOLDER-NAME` then start with that path.

If `$ARGUMENTS` is empty, ask for the Jira key. After spec approval (`SPEC_APPROVED` or `APPROVED` in the run dir):

**Cursor** (`runtime.agent: cursor`):

```bash
dev-loop step KEY --repo PATH
```

Each `step` is one stage. Write `STAGE_DONE` then `step` again. Test-writer uses a new Agent.

**Claude Code:**

```bash
dev-loop continue KEY --repo PATH
```

Requires GitHub remote, `gh` auth, and Atlassian secrets in `~/.config/dev-conductor/secrets.env`. No Jira/GitHub MCP.

Example config leases a treehouse worktree (`git.isolation: treehouse`) and caps concurrent tickets at `queue.max_active: 3`. Eval config sets isolation `none`.
