---
name: code-review
description: Use after a feature, before merge or PR, or when the user asks for a review. Spawn the code-reviewer agent on the diff, not this session's chat history.
---

# Code review

Review the **work product**, not the author's chain of thought.

## When

- After a non-trivial feature or bugfix
- Before commit/PR when the user wants a check
- When stuck and a second pass would help

## How

1. `git diff` (or named SHAs) is the scope unless the user names files.
2. Spawn the **code-reviewer** agent with: what changed, what it should do, base/head if known.
3. Act on critical/major findings. Do not rubber-stamp.

## Do not

- Ask the reviewer to re-implement
- Paste secrets
- Treat style nits as blockers unless the project rules say so

If a finding is a missing durable convention, flag it for the parent to apply via `agent-memory`. The reviewer does not Write metadata files.
