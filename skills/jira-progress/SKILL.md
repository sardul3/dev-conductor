---
name: jira-progress
description: Move a Jira issue across configured workflow columns and comment as /dev-loop progresses. Use when starting a story, opening a PR, merging, blocking, or waiting. REST only, not Jira MCP.
---

# Jira progress

Use the CLI. Column names live in `~/.config/dev-conductor/dev-loop/config.yaml` under `workflow:`.

```bash
python3 ~/.claude/hooks/dev-loop/cli.py jira-progress KEY --event on_start|on_pr|on_merge|on_block|on_waiting --comment "..."
```

Requires `workflow.enabled: true` and `ATLASSIAN_*` (or `jira.auth: none` against fake Jira). Transitions are looked up **by name**. If the board uses different names, change the yaml — do not hardcode IDs.

On merge, the CLI also comments the sprint deploy ticket (`workflow.deploy_ticket_key` or first hit of `deploy_ticket_jql`).

Do not use Jira MCP.
