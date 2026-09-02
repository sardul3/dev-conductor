---
name: finish-branch
description: After ad-hoc implementation is done and tests pass, offer merge, PR, or leave-the-branch. Use when the user asks to finish this branch, open a PR, or merge — and this is NOT a /dev-loop ticket. For /dev-loop, ship is cli.py step / continue; do not use this skill.
---

# Finish a development branch

Ship for `/dev-loop` is the conductor (`step` / `continue`). This skill is for **manual** branches so Superpowers-style finishes still exist.

If the cwd or prompt is a `/dev-loop` run (ticket key, `runs/KEY/`, `prompt-*.md`): stop. Do not merge, push, or `gh pr create`. Tell the user to `python3 ~/.claude/hooks/dev-loop/cli.py step KEY` after `STAGE_DONE`.

## Ad-hoc branches only

1. **Verify** — run the project test/build command (`verify-before-done`). Stop if red.
2. **Detect** — git repo? GitHub remote? `gh` auth? Current branch vs `main`/`master`.
3. **Offer options** (do not push or open a PR unless the user asked):
   - Merge locally to main
   - Push and open a PR (`gh pr create`)
   - Leave the branch; print the exact commands
4. **Execute** the chosen option. Never force-push main. Never skip hooks unless asked.
5. **Cleanup** only if the user wants the local branch deleted after merge.

If this is a prompt-enrich **work** session, keep the recap short (`implement-terse`).
