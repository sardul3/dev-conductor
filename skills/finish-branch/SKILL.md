---
name: finish-branch
description: Use when implementation is done and tests pass, and you need merge, PR, or cleanup options.
---

# Finish a development branch

1. **Verify** — run the project test/build command (`verify-before-done`). Stop if red.
2. **Detect** — git repo? GitHub remote? `gh` auth? Current branch vs `main`/`master`.
3. **Offer options** (do not push or open a PR unless the user asked):
   - Merge locally to main
   - Push and open a PR (`gh pr create`)
   - Leave the branch; print the exact commands
4. **Execute** the chosen option. Never force-push main. Never skip hooks unless asked.
5. **Cleanup** only if the user wants the local branch deleted after merge.

If this is a prompt-enrich **work** session, keep the recap short.
