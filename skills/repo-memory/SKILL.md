---
name: repo-memory
description: Load or rebuild the hashed repo index for /dev-loop. Use when you need repo context and should skip Explore if the index is still valid.
---

# Repo memory

```bash
python3 ~/.claude/hooks/dev-loop/cli.py memory [--repo PATH] [--force]
```

`~/.config/dev-conductor/dev-loop/memory/<repo-folder>/` (`HASH`, `INDEX.md`, `contracts.md`). If HASH matches tracked files + HEAD, **do not Explore**. If invalid, regenerate. No embeddings. Contract globs are config (`memory.contract_globs`).
