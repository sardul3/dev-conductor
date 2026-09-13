# Assembled prompt shape

The handoff file (Claude `launch-clean-claude.sh` or Cursor `~/.config/dev-conductor/handoffs/`) must start with the skip marker so the next session does not re-enrich. Do not use this file for `/dev-loop` spec — that stays in-chat as `spec.md`.

```markdown
<!-- PROMPT_CONTRACT_V1 -->
# Task
<short title>

## Role
...

## Audience
...

## Goal
...

## Context
...

## Constraints
...

## Output format
...

## Length and tone
...

## Success criteria
...

## Model
- backend: ccr | anthropic
- profile: code
- model: <filled at launch>
- fallback: <filled at launch>
- why: <one line>
- override: <optional alias or profile>

## Original user request
...
```

Do not paste secrets. Point at files that already exist instead of dumping them.
