---
name: restate-plain
description: Re-pitch the current state in plain technical English when the last message did not land. Use when the user is lost, says wait-what, huh, or asks you to say that again without jargon.
disable-model-invocation: true
---

# Restate plain

The user is lost. Another dense paragraph will not help. Stop the grill or implementation recap and re-pitch.

1. Two sentences of context (where we are in the work)
2. What was just proposed or done, in simple technical English (short sentences, one idea each, no slang, no stacked clauses)
3. If `CONTEXT.md` or `CONTEXT-MAP.md` exists, use those terms only

Then ask one question: did that match what they thought was happening?

## Example (shape)

> We are still on the spec for LAB-1, not writing code. I asked whether `/health` should stay unauthenticated. You said yes. Next I will write that into spec.md and ask you to approve the spec — not the ticket. Does that match what you thought was happening?
