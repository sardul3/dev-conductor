---
name: prompt-contract
description: Fill the nine-slot prompt contract, then grill, then hand off to a clean Claude session. Use for new substantial tasks. Do not implement in this session.
---

# Prompt contract

You are in the **enrichment** session. Do **not** implement the user's task here. Do not open extra Cursor tabs. The work happens in a new `claude` CLI terminal after launch.

If the user typed `/deep-ask ...`, treat the rest of the message as the original request.

## 1. Fill these nine slots

Infer when obvious. Ask only for missing **high-impact** slots. Multiselect is allowed for role, audience, and length/tone. Do not ask for a raw model id unless they volunteer an override (`opus`, `sonnet`, `ultra`, or a profile name).

| # | Slot | Notes |
| - | ---- | ----- |
| 1 | Role | senior backend, staff SRE, tech lead, security reviewer, … |
| 2 | Audience | implementing agent, PR reviewer, beginner, future-you |
| 3 | Goal | one-sentence deep ask **and** the deliverable |
| 4 | Context | repo, stack, files, constraints; or “none / infer from repo” |
| 5 | Constraints / non-goals | must / must not |
| 6 | Output format | code+tests, plan only, diff, ADR, commands |
| 7 | Length / tone | short, informal, rigorous, production-ready |
| 8 | Success criteria | observable done-when |
| 9 | Model profile | `fast` `code` `reason` `heavy` `vision` (auto; user may override) |

Profile tie-break: vision if screenshots/UI; else heavy if many files / production / security; else reason if debug/design/investigate; else code if the output is code/tests; else fast.

Optional (only if they change the work): examples, tools/sources, plan-then-code vs jump-to-code.

See `reference.md` in this skill for the assembled markdown shape.

## 2. Grill

Follow `~/.claude/skills/design-tree-interview/SKILL.md` (or `/grill-plan`). Fill remaining contract slots from the tree. Escape: “just go”, “skip grill”, `/skip-enrich`. If they get lost, `restate-plain`.

## 3. Handoff and launch

When the frontier is empty (or they skip):

1. Follow `~/.claude/skills/session-handoff/SKILL.md`. Start the file with `<!-- PROMPT_CONTRACT_V1 -->` and include the nine slots plus original request.
2. Run (replace the path with the file you wrote):

```bash
~/.claude/hooks/prompt-enrich/launch-clean-claude.sh --file <handoff-path>
```

3. Tell the user the saved path and that **work continues in the new terminal**. Suggest that session load `implement-terse`.
4. Stop. Do not start coding in this session. The new tab is the only implementer; this tab continuing will 429 OpenRouter.
