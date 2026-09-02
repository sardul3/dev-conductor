---
name: repo-memory
description: Load or rebuild the hashed repo index so /dev-loop skips a fresh Explore. Use at the start of spec or whenever you need repo context and HASH may still be valid. Use --force only when the index is wrong, not as a default.
---

# Repo memory

Explore is expensive and often duplicates `INDEX.md`. If HASH still matches tracked files + HEAD, read the index and stop.

```bash
python3 ~/.claude/hooks/dev-loop/cli.py memory [--repo PATH] [--force]
```

Files: `~/.config/dev-conductor/dev-loop/memory/<repo-folder>/` (`HASH`, `INDEX.md`, `contracts.md`).

- HASH valid → **do not Explore**. Use `INDEX.md` + `contracts.md` for spec seams.
- HASH invalid or missing → regenerate, then read the new files.
- `--force` when you know the index is stale in a way HASH missed (rare).

No embeddings. Contract globs are config (`memory.contract_globs`). Do not paste the index into `AGENTS.md`.
