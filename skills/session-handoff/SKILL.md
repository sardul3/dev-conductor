---
name: session-handoff
description: Compact this conversation into a handoff file for a fresh agent. Use when launching a clean Claude session, spawning a new Cursor Agent after a grill, or the user asks for a handoff. Do not hand off a /dev-loop spec — stay in-chat and write spec.md.
---

# Session handoff

A new agent has none of this chat. The file must be enough to continue **without** re-grilling locked decisions.

Do **not** use this for `/dev-loop` spec (`story-spec` stays in this chat). Do **not** use the project Write tool for `/tmp` (sandboxed; writes are rejected). Do **not** write the handoff into the repo.

## Where to write

**Claude Code:**

```bash
python3 ~/.claude/hooks/prompt-enrich/save_handoff.py <<'EOF'
<!-- PROMPT_CONTRACT_V1 -->

# Prompt contract
...
EOF
~/.claude/hooks/prompt-enrich/launch-clean-claude.sh --file <that-path>
```

**Cursor:** write the same body under `~/.config/dev-conductor/handoffs/` (not via project Write if sandboxed), then spawn a **new Agent** with that file as the prompt. Do not run `launch-clean-claude.sh`.

Then stop. Do not implement in this session.

## Must include

- Goal of the **next** session (use the user’s argument if present)
- Shared understanding (decisions already locked)
- Open questions
- Paths or URLs to specs, plans, ADRs, issues, commits — **do not paste those files**
- Suggested skills the next agent should load
- Model profile recommendation (`fast` `code` `reason` `heavy` `vision`) if known

Start the file with `<!-- PROMPT_CONTRACT_V1 -->`. Assembled shape: `prompt-contract` [reference.md](../prompt-contract/reference.md).

## Must not

- Duplicate long specs already on disk
- Include API keys, passwords, tokens, or unnecessary PII
- Instruct the next agent to re-run the grill unless the frontier is still non-empty
- Write under `/tmp` or `$TMPDIR`
