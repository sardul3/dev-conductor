---
name: prompt-contract
description: Fill the nine-slot prompt contract, grill with design-tree-interview, then hand off. Use for new substantial ad-hoc tasks, /deep-ask, or prompt-enrich. If the prompt already loaded story-spec or names a /dev-loop ticket, do not hand off to an implement session — stay on spec.md.
---

# Prompt contract

You are in the **enrichment** session. Do **not** implement the user's task here.

If the user typed `/deep-ask ...`, treat the rest of the message as the original request.

## `/dev-loop` spec (short circuit)

If the prompt says `story-spec`, includes a ticket key + run dir, or `issue.md` is the source of requirements: load `story-spec` and `design-tree-interview` **spec mode** only. Do not run `session-handoff` or `launch-clean-claude.sh`. Infer contract slots silently if they help the grill; the deliverable is `spec.md`.

## Ad-hoc tasks

### 1. Fill these nine slots

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

Assembled markdown shape: [reference.md](reference.md).

### 2. Grill

Follow `design-tree-interview` (mode B Cursor or C Claude enrich). Escape: “just go”, “skip grill”, `/skip-enrich`. If they get lost, `restate-plain`.

### 3. Handoff

When the frontier is empty (or they skip):

1. Follow `session-handoff`. Start the file with `<!-- PROMPT_CONTRACT_V1 -->`.
2. **Cursor:** new Agent on the handoff path. Stop.
3. **Claude Code:** `~/.claude/hooks/prompt-enrich/launch-clean-claude.sh --file <handoff-path>`. Work continues in that terminal. Stop here (two sessions on OpenRouter will 429).
