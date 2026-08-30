---
name: agent-memory
description: Persist durable agent metadata after self-review, user review, PR comments, or a correction. Use when verdict.json, review feedback, or a user correction implies a missing convention, term, or stack law.
---

# Agent memory

Feedback is wasted if the next session repeats the same miss. When self-review (`verdict.json` / spawned `code-reviewer`) or user review (chat correction, PR comments) lands, update **one relevant file**. Do not batch. Do not invent.

## When

- Self-review wrote `verdict.json` and a finding is a **durable** convention (handshake, isolation, secrets, MCP ban, naming), not a one-off bug.
- User or PR review corrects how agents should work on this repo or stack.
- A domain term or hard-to-reverse decision was resolved (`domain-glossary`).

Skip: one-ticket AC, style nits, speculative rewrites, secrets, SessionStart text.

## Where (pick one)

| Signal | File | Rule |
| ------ | ---- | ---- |
| Convention every future agent on **this repo** must keep | that repo's `AGENTS.md` (or `CLAUDE.md` if it only `@`-includes AGENTS) | Rewrite or prune. No procedure dumps. |
| Stack law missing for a path (Java, Python, TS, k8s, …) | path-scoped `.claude/rules` / `.cursor/rules` / repo `.envfiles/rules` | `alwaysApply: false` + `globs`. Never always-on. |
| Domain term | `CONTEXT.md` via `domain-glossary` | Glossary only. |
| Hard to reverse + surprising + real trade-off | `docs/adr/` via `domain-glossary` | Skip unless all three. No empty ADRs. |
| Install / usage / public API would be wrong | `README.md` | That case only. |

The **reviewer is read-only**. It flags a metadata gap in the verdict (`metadata` or a risk). The **parent** (review skill, writer, or `pr-comment-fixer`) writes the file.

## Do not

- Invent ADRs or always-on rules.
- Stow notes into SessionStart or CLAUDE.md tax.
- Update conductor secrets, hooks, or `~/.config/dev-conductor/secrets.env`.
- Copy skill bodies into AGENTS.md.
- Treat `SPEC_APPROVED` as ticket-done or chat as the source of Jira AC.
