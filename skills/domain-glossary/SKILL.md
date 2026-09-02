---
name: domain-glossary
description: Maintain CONTEXT.md as a glossary and write sparse ADRs when a decision is hard to reverse. Use when sharpening domain language, the user contradicts an existing term, grill-plan-docs is running, or a review resolved a named concept. Do not dump implementation notes into the glossary.
---

# Domain glossary

This is for **changing** the domain model, not for merely reading vocabulary. Vague words in a spec become tests that spy on the wrong objects.

## Layout

Single context:

```
CONTEXT.md
docs/adr/
```

Multiple contexts: root `CONTEXT-MAP.md` points at each bounded context’s `CONTEXT.md` and local `docs/adr/`.

Create files only when you have content. First resolved term → create `CONTEXT.md`. First real architectural trade-off → create `docs/adr/`.

## During the session

- If the user contradicts `CONTEXT.md`, stop and pick one meaning.
- Replace vague words with one canonical term.
- Stress-test relationships with concrete edge-case scenarios.
- If they describe behavior, check the code. Surface mismatches.
- Update `CONTEXT.md` **when the term is resolved**, not in a batch at the end.
- `CONTEXT.md` is a **glossary only**. No implementation details, no scratch notes.

## Glossary shape

```markdown
# Glossary

## Term
One-paragraph definition. Example in the domain. Not-this (what people confuse it with).
```

## ADRs (rare)

Offer an ADR only when all three hold: hard to reverse, surprising without context, real trade-off. Skip otherwise.

```markdown
# NNNN - Title

## Context
## Decision
## Consequences
```

When feedback (self-review or user/PR review) resolves a term or hard-to-reverse decision, update here. For non-glossary conventions (AGENTS.md, path-scoped rules), load `agent-memory` instead.

In `/dev-loop` spec, keep acceptance in `spec.md`. Glossary updates are extra, not a substitute for seams.
