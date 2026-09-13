---
name: grill-plan
description: User-invoked design grill for an ad-hoc plan. Use when the user says grill me, stress-test this plan, or /grill-plan. If the prompt is a /dev-loop ticket or story-spec, use design-tree-interview spec mode instead — write spec.md, do not hand off.
disable-model-invocation: true
---

# Grill plan

Read and follow `design-tree-interview`. Pick the ending from that skill:

- **A** `/dev-loop` spec → `spec.md`, stop (no implement, no Claude launch).
- **B** Cursor ad-hoc → `session-handoff` into `~/.config/dev-conductor/handoffs/`, new Agent.
- **C** Claude prompt-enrich → Read only stack manifests, `save_handoff.py`, `launch-clean-claude.sh`.

Do not implement. Do not skip looking up facts (except enrich mode C, which is Read-only on manifests).
