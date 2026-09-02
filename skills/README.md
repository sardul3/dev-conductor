# Skills in this repo (dev-conductor)

Installed to `~/.claude/skills/` by `./claude/prompt-enrich/install-skills.sh`.

**Lazy.** Descriptions are a small catalog tax; bodies load when relevant. Do not paste these into `CLAUDE.md`.

Source of truth is this directory. Plugin and Cursor install from here (`plugins/dev-loop/skills` is a symlink; Cursor `install.sh` copies these folders).

## Loop

| Skill | Use |
| ----- | --- |
| `dev-loop` | `/dev-loop KEY` conductor |
| `story-spec` | Grill Jira → `spec.md` |
| `test-writer` | Failing tests; no impl Read |
| `repo-memory` | Hashed repo index |
| `dev-loop-review` | `verdict.json` via `code-reviewer` |
| `pr-comment-fixer` | Address PR review comments |
| `jira-progress` | Jira REST column moves + comments |
| `agent-memory` | Durable conventions from `verdict.json` `metadata[]` |
| `lavish-ui` | Spike: Lavish HTML review for UI/UX tickets only |

## Coding / ops (used by the loop)

| Skill | Use |
| ----- | --- |
| `tdd` | Test first |
| `systematic-debugging` | Root cause before patch |
| `verify-before-done` | Proof before “done” |
| `code-review` | Spawn `code-reviewer` on the diff |
| `finish-branch` | Ad-hoc merge/PR options — **not** `/dev-loop` ship |
| `implement-terse` | Work-session tone |
| `token-playbook` | Where context should live |

## Prompt-enrich (grill)

`prompt-contract`, `design-tree-interview`, `grill-plan`, `grill-plan-docs`, `session-handoff`, `domain-glossary`, `restate-plain`, `grill-deep-ask`

## Architecture / UI spec (optional)

Not part of `/dev-loop`. Cursor install still copies it with the other skills.

| Skill | Use |
| ----- | --- |
| `arch-studio` | Canonical `.arch.json` → draw.io, `review.html`, Azure/K8s gates, UI spec. Discovery uses `design-tree-interview`. |

## Agents

`claude/agents/` → `~/.claude/agents/` via `./claude/install-agents.sh`. Keep the set small: **code-reviewer**, **debugger**, **code-simplifier**. Descriptions are always-on in the Task picker.
