---
name: pr-comment-fixer
description: Address GitHub PR review comments for a watched /dev-loop PR using gh (not GitHub MCP). Use when the poller wrote pr-comments.md, checks failed, or the user says address PR comments / fix the review. Stay on the feature branch; do not force-push.
---

# PR comment fixer

Comments are cheap to ignore and expensive to bounce. Classify once, then either fix or explain on the PR.

Input: `pr-comments.md` in `~/.config/dev-conductor/dev-loop/runs/KEY/`.

## Procedure

1. Read comments. Classify each: **simple** (rename, import, typo, obvious test) vs **needs reasoning** (design, API shape, security). Ignore comments that only restate the code. If a comment is factually wrong about the diff, say so in a `gh pr comment` note.
2. Simple → implement with `tdd` (failing test if behavior changes, then code). Do not weaken tests except compile/syntax/simple IO or a spec contradiction.
3. Needs reasoning → decide in this session, then implement. Do not bounce to another agent for nits.
4. Stay on the feature branch. Conventional commit (`feat`/`fix` + Jira key). Never commit to `main`/`master`. Never force-push. Never rewrite pushed history.
5. `gh pr comment N --body "..."` a short note. Re-request review with `gh` (`gh pr edit --add-reviewer` if needed).
6. If a comment corrects a **durable** agent convention (handshake, isolation, secrets, stack law), load `agent-memory` (or `metadata[]` + `cli.py agent-memory`) before handshake. Skip one-ticket nits.
7. Write `STAGE_DONE` and `SESSION_DONE`.

Do not use GitHub MCP or Jira MCP. Do not run `finish-branch`.
