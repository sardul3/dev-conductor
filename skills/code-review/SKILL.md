---
name: code-review
description: Spawn the code-reviewer agent on a git diff, not this chat’s history. Use after a feature, before an ad-hoc merge or PR, or when the user asks for a review. For /dev-loop tickets, load dev-loop-review instead (verdict.json + handshake).
---

# Code review

Review the **work product**, not the author's chain of thought. Chat history includes discarded approaches that will bias a rubber stamp.

## `/dev-loop`

Load `dev-loop-review`. That skill writes `verdict.json` and `STAGE_DONE`. This one does not.

## Ad-hoc

- After a non-trivial feature or bugfix
- Before commit/PR when the user wants a check
- When stuck and a second pass would help

1. `git diff` (or named SHAs) is the scope unless the user names files.
2. Spawn **code-reviewer** with: what changed, what it should do, base/head if known.
3. Act on critical/major findings. Do not rubber-stamp.

Do not ask the reviewer to re-implement. Do not paste secrets. Style nits are not blockers unless project rules say so.

If a finding is a missing durable convention, flag it for the parent via `agent-memory`. The reviewer does not Write `AGENTS.md` or rules.
