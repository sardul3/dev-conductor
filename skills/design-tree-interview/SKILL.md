---
name: design-tree-interview
description: Relentless design-tree interview. Use when stress-testing a plan, grilling a design, or filling a deep-ask contract. Explores the repo for facts; asks the user only for decisions.
---

# Design-tree interview

Interview until shared understanding. Treat the work as a **design tree**: each decision unlocks the decisions that depend on it.

## Rounds

The **frontier** is every question whose prerequisites are already settled. Ask the **whole frontier** in one round. Number each item. Give **your recommended answer** every time. Then wait.

```
❓ **Q1** - **<title>**: <body, choices if useful>

➡️ <recommended answer>

---

❓ **Q2** - **<title>**: ...

➡️ <recommended answer>
```

After answers, recompute the frontier. A question that still depends on an open Q in this round belongs in a **later** round.

## Facts vs decisions

- **Facts** (filesystem, git, tests, types, existing APIs): look them up. Do not ask the user.
- **Decisions** (product, trade-offs, taste): ask the user. Wait.

### Prompt-enrich session (injected; no repo explore)

You cannot Glob, Grep, Explore, or spawn agents. For facts, **Read only** these files if they exist in cwd: `README.md`, `package.json`, `pyproject.toml`, `go.mod`, `Cargo.toml`, `composer.json`. Infer stack from those. Do not ask the user whether the app is Python vs Node if `package.json` or `pyproject.toml` already says.

`AskUserQuestion` allows **at most 4 options** per question. If you need more choices, ask in numbered markdown instead.

When the frontier is empty, follow `session-handoff` (pipe to `save_handoff.py`, never Write to `/tmp`) and run `~/.claude/hooks/prompt-enrich/launch-clean-claude.sh --file <handoff-path>`. Stop after launch.

Otherwise (not an enrich session): dispatch a subagent if the search is large. A running lookup is an unsettled prerequisite only for questions that depend on it; ask the rest of the frontier now.

## Stop

The frontier is empty: every branch visited, nothing silently assumed. Do **not** implement until the user confirms shared understanding.

If this interview is feeding the prompt-enrich pipeline, also fill the nine contract slots (role, audience, goal, context, constraints, format, length/tone, success criteria, model profile) from the tree; infer slots you already know. Then follow `session-handoff`. Stop after launch.
