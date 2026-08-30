---
name: restate-plain
description: Last message did not land. Restate it in plain technical English. Use when the user is lost, says wait-what, or asks for a re-pitch.
disable-model-invocation: true
---

# Restate plain

Stop. Re-pitch the current state:

1. Two sentences of context (where we are in the work)
2. What was just proposed or done, in simple technical English (short sentences, one idea each, no slang, no stacked clauses)
3. If `CONTEXT.md` or `CONTEXT-MAP.md` exists, use those terms only

Then ask one question: did that match what they thought was happening?
