---
name: grill-plan
description: User-invoked design grill. Use when the user says grill me, stress-test this plan, or /grill-plan.
disable-model-invocation: true
---

# Grill plan

Read and follow `design-tree-interview` (same repo or `~/.claude/skills/design-tree-interview/SKILL.md`).

Do not implement. Do not skip looking up facts in the codebase.

In a prompt-enrich session, Read only cwd `README.md` / `package.json` / `pyproject.toml` (no Glob/Grep/Explore). Handoff via `save_handoff.py`, never Write to `/tmp`.
