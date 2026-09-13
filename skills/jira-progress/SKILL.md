---
name: jira-progress
description: Move a Jira issue across configured workflow columns and comment as /dev-loop progresses. Use when the user asks to transition/comment a ticket, or when you are blocked/waiting outside the automatic CLI events. REST only — never Jira MCP.
---

# Jira progress

Column names live in `~/.config/dev-conductor/dev-loop/config.yaml` under `workflow:`. `start` fires `on_start` (CLI-owned) and assigns the current user when unassigned. Later lifecycle points fire `on_pr` / `on_merge` / `on_block` / `on_waiting`. Do not double-transition because a stage finished. `workflow.enabled` defaults on; eval (`config.test.yaml`) turns it off.

```bash
python3 ~/.claude/hooks/dev-loop/cli.py jira-progress KEY --event on_start|on_pr|on_merge|on_block|on_waiting --comment "..."
```

Requires `workflow.enabled` (default true) and `ATLASSIAN_*` (or `jira.auth: none` against fake Jira). Transitions are looked up **by name**. If the board uses different names, change the yaml — do not hardcode IDs. Skip/fail prints `dev-loop: jira …` and is recorded on the run (`progress.md` stage `jira`).

On merge, the CLI also comments the sprint deploy ticket (`workflow.deploy_ticket_key` or first hit of `deploy_ticket_jql`).

Use this skill when the user asks, or when you are **stuck** and need `on_block` / `on_waiting` with a real comment. Do not use Jira MCP. Chat is not the source of acceptance criteria (`story-spec` / `spec.md` is).
