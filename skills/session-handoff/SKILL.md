---
name: session-handoff
description: Compact this conversation into a handoff file for a fresh agent. Use when launching a clean Claude session or when the user asks for a handoff.
argument-hint: "What the next session should focus on"
disable-model-invocation: true
---

# Session handoff

Write a handoff so a **new** agent can continue.

**Do not use the Write tool** (it is sandboxed to the git worktree; `/tmp` writes are rejected). **Do not write into the project.**

Pipe markdown to the saver, then launch:

```bash
python3 ~/.claude/hooks/prompt-enrich/save_handoff.py <<'EOF'
<!-- PROMPT_CONTRACT_V1 -->

# Prompt contract
...
EOF
```

The command prints a path under `~/.claude/prompt-enrichment/runs/`. Immediately run:

```bash
~/.claude/hooks/prompt-enrich/launch-clean-claude.sh --file <that-path>
```

Then stop. Do not implement in this session.

## Must include

- Goal of the **next** session (use the user’s argument if present)
- Shared understanding (decisions already locked)
- Open questions
- Paths or URLs to specs, plans, ADRs, issues, commits — **do not paste those files**
- Suggested skills the next agent should load
- Model profile recommendation (`fast` `code` `reason` `heavy` `vision`) if known

Start the file with `<!-- PROMPT_CONTRACT_V1 -->`.

## Must not

- Duplicate long specs already on disk
- Include API keys, passwords, tokens, or unnecessary PII
- Instruct the next agent to re-run the grill unless the frontier is still non-empty
- Write under `/tmp` or `$TMPDIR`
