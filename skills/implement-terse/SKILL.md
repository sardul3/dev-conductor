---
name: implement-terse
description: Terse implement-mode output after a handoff or in a /dev-loop writer session. Use in clean work sessions, not during design-tree interviews, story-spec, or when the user asked for a tutorial.
disable-model-invocation: true
---

# Implement terse

For **implementation** replies only. Interviews need full sentences; this skill would wreck a grill.

- No greeting, no recap of the user message, no “happy to help”.
- Lead with the change or the command.
- Bullets over paragraphs. Skip hedging.
- Do not restate code you just wrote.
- If a test or lint failed, paste the failing assertion or error line, not the whole log.
- If the user asked for depth, diagrams, or a tutorial, drop this skill and write normally.

Never apply this while running `design-tree-interview`, `grill-plan`, `story-spec`, or `restate-plain`.
