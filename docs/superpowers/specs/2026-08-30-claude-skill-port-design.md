# Claude skill/agent port (from Cursor snapshot)

Date: 2026-08-30  
Status: implemented  
Repo: `dev-conductor`

## Goal

Give Claude Code (and other agents that read `~/.claude/skills` / `~/.claude/agents`) the **generic** Cursor workflows that improve coding, design, and setup. Do **not** copy Cursor-product skills. Keep agent count tiny: descriptions are always-on.

## Port

| Skill | Why |
| ----- | --- |
| `tdd` | Work-session quality; already a user preference |
| `systematic-debugging` | Stops random patches |
| `verify-before-done` | Evidence before “done” |
| `code-review` | How to spawn the reviewer agent |
| `frontend-design` | UI without templated defaults |
| `tutorial-writer` | Docs/onboarding |
| `find-skills` | Discover more skills instead of inventing |
| `finish-branch` | Tests → PR/merge choice |
| `skill-author` | Add skills without dumping skill-creator |

| Agent (`~/.claude/agents`) | Why |
| -------------------------- | --- |
| `code-reviewer` | Isolated review, no session history |
| `debugger` | Root-cause pass |
| `design-lead` | UI in a separate context |

## Do not port (removed from repo)

Cursor-product `skills-cursor`, plugin-skill caches, marketplace dumps, and plugin agents are not snapshotted. Collect/install skip them. Cursor plugins reinstall themselves.

## Install

`claude/prompt-enrich/install-skills.sh` copies `skills/`. `claude/install-agents.sh` copies `claude/agents/` → `~/.claude/agents/`.
