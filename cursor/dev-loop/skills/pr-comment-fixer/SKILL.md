---
name: pr-comment-fixer
description: Fix GitHub PR review comments for a watched /dev-loop PR. Use when the poller launches a fixer, checks failed, or the user says address PR comments. Use gh, not GitHub MCP.
---

# PR comment fixer

Input: `pr-comments.md` in the run dir (`~/.config/dev-conductor/dev-loop/runs/KEY/`).

1. Read comments. Classify each: **simple** (rename, import, typo, obvious test) vs **needs reasoning** (design, API shape, security).
   Ignore comments that only restate the code. If a comment is factually wrong about the diff, say so in the `gh pr comment` note.
2. Simple → implement with `tdd` (failing test if behavior changes, then code). Do not weaken tests except compile/syntax/simple IO or a spec contradiction.
3. Needs reasoning → decide in this session, then implement. Do not bounce to another agent for nits.
4. Stay on the feature branch. Conventional commit (`feat`/`fix` + Jira key). Never commit to `main`/`master`. Never force-push. Never rewrite pushed history.
5. `gh pr comment N --body "..."` a short note. `gh pr edit --add-reviewer` / re-request review with `gh`.
6. Write `STAGE_DONE` in the run dir.

Do not use GitHub MCP or Jira MCP.
