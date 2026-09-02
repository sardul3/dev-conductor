# Dev-loop extras (read when caps, isolation, or poller matter)

## Isolation

Default `git.isolation: worktree` — native worktree under `.{repo}-worktrees/{KEY}`. `treehouse` is opt-in. Eval uses `isolation: none`. `queue.max_active` (default 3) is concurrent in-progress tickets, not tmux fan-out. A fourth start exits until one ships or you release its worktree.

Start from the clone under `~/dev` (`git.allow_outside_dev` default false).

## Caps

`caps.max_launches` / `max_tokens` / `max_budget_usd` / `wall_sec` — `0` means off. When hit, the run dir gets `STOPPED`. Unattended profiles still need these set; they do not default on.

## Poller

`$CLI poll` / `install-poller`. Launchd loads only if `poller.enabled`. Uses `gh`, not GitHub MCP.

## Brief I/O

New connector: subclass `brief.Connector`, implement `fetch()`. Disk files stay JSON.
