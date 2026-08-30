# Assembled prompt shape

The handoff file launched by `launch-clean-claude.sh` must start with the skip marker so the next session does not re-enrich.

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
