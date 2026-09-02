# Prompt enrich (optional)

Ad-hoc task grill for Claude Code — **not required for `/dev-loop`**. Cursor users grill in-chat via `story-spec`.

```bash
./claude/prompt-enrich/install.sh
python3 -m unittest discover -s claude/prompt-enrich/tests -v
```

Or install with the full product:

```bash
./install.sh --with-enrich
```

## Defaults

- **Stock Claude Code auth** (`apiKeyHelper` / Anthropic). No OpenRouter or CCR setup.
- Model profiles in `model-router.yaml` map to Claude aliases (`haiku`, `sonnet`, `opus`).
- Classifier uses `haiku` via the Anthropic Messages API when a key is available.

## Behavior

- New-task prompts inject skill names only (`prompt-contract` → grill → `launch-clean-claude.sh`).
- Follow-ups, slash commands, and `<!-- PROMPT_CONTRACT_V1 -->` skip (deterministic).
- Other prompts: one tiny classify call (Y/N). Timeout/error → skip (fail open). `/deep-ask` forces grill.
- `PROMPT_ENRICH_DISABLE=1` turns enrich + brevity + compress off. `/skip-enrich` skips one prompt.

## Optional CCR / OpenRouter

Power users only. Not installed or configured by default.

```bash
cp claude/prompt-enrich/model-router.ccr.yaml ~/.claude/hooks/prompt-enrich/
export PROMPT_ENRICH_BACKEND=ccr
```

Spec: `docs/superpowers/specs/2026-08-29-prompt-enrichment-design.md`.
