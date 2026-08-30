# Skills in this repo (dev-conductor)

Installed to `~/.claude/skills/` by `./claude/prompt-enrich/install-skills.sh`.

**Lazy.** Descriptions are a small catalog tax; bodies load when relevant. Do not paste these into `CLAUDE.md`.

Source of truth is this directory. Cursor copies live in `cursor/dev-loop/skills/` — do not edit `skills/` only to make Cursor work; edit here, then re-run `cursor/dev-loop/install.sh`.

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

## Coding / ops (used by the loop)

| Skill | Use |
| ----- | --- |
| `tdd` | Test first |
| `systematic-debugging` | Root cause before patch |
| `verify-before-done` | Proof before “done” |
| `code-review` | Spawn `code-reviewer` on the diff |
| `finish-branch` | Tests then merge/PR options |
| `implement-terse` | Work-session tone |
| `token-playbook` | Where context should live |

## Prompt-enrich (grill)

`prompt-contract`, `design-tree-interview`, `grill-plan`, `grill-plan-docs`, `session-handoff`, `domain-glossary`, `restate-plain`, `grill-deep-ask`

## Not in this repo

Product/design skills (`frontend-design`, `tutorial-writer`, `ase-lifecycle`, `find-skills`, `skill-author`) live in `~/dev/mac-ai-setup`. Cursor-product skills come from Cursor plugins.

## Agents

`claude/agents/` → `~/.claude/agents/` via `./claude/install-agents.sh`. Keep the set small: **code-reviewer**, **debugger**, **code-simplifier**. Descriptions are always-on in the Task picker.
