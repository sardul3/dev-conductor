---
name: design-tree-interview
description: Relentless design-tree interview until the frontier is empty. Use when grilling a /dev-loop spec, stress-testing a plan, filling a prompt-contract, or the user says grill me / design interview. Looks up facts; asks the user only for decisions. Do not implement during the interview.
---

# Design-tree interview

Treat the work as a **design tree**: each decision unlocks the decisions that depend on it. Asking one isolated question wastes rounds; asking internals the filesystem already answers wastes the user's attention.

## Rounds

The **frontier** is every question whose prerequisites are already settled. Ask the **whole frontier** in one round. Then wait.

### Cursor (spec, `/dev-loop`, ad-hoc grill in Agent chat)

Use the **AskQuestion** tool — never markdown `❓ Q1` in the user-visible reply. One AskQuestion call may include several questions.

- Recommended answer = **first** option; end that label with `(Recommended)`.
- At most **4** options per question (Cursor adds Other).
- Do not paste CLI `--help`, argparse usage, or raw stderr.

### Claude Code enrich

`AskUserQuestion` allows **at most 4 options** per question; otherwise numbered markdown:

```
❓ **Q1** - **<title>**: <body, choices if useful>

➡️ <recommended answer>
```

After answers, recompute the frontier. A question that still depends on an open Q in this round belongs in a **later** round.

## Facts vs decisions

- **Facts** (filesystem, git, tests, types, existing APIs): look them up. Do not ask the user.
- **Decisions** (product, trade-offs, taste): ask the user. Wait.

## Which ending (pick one)

**A — `/dev-loop` spec** (prompt loaded `story-spec`, or run dir has `issue.md`):

Empty frontier → write `spec.md` per `story-spec`. Stop. Do **not** implement, `session-handoff`, or `launch-clean-claude.sh`. The user still has to approve the spec (AskQuestion).

**B — Cursor ad-hoc grill** (user asked to grill a plan, not a ticket):

Empty frontier → `session-handoff` into `~/.config/dev-conductor/handoffs/`. Spawn a new Cursor Agent with that file. Stop.

**C — Claude prompt-enrich** (injected enrich session; no Glob/Grep/Explore/Agent):

For facts, **Read only** cwd `README.md`, `package.json`, `pyproject.toml`, `go.mod`, `Cargo.toml`, `composer.json`. Infer stack from those.

Empty frontier → fill remaining prompt-contract slots, `session-handoff` via `save_handoff.py` (never Write `/tmp`), `launch-clean-claude.sh --file <path>`. Stop after launch. Do not implement in this tab.

## Stop

Frontier empty means every branch visited, nothing silently assumed. Do **not** implement until the user confirms shared understanding (spec approve, or they skip grill).
