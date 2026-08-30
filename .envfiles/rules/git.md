# Git (do not install as an unscoped rule)

Prefer these bullets in `~/.claude/CLAUDE.md`. Installing this file under `~/.claude/rules/` without `paths:` is a second always-on CLAUDE.md.

- Never commit secrets, `.env`, or SSH private keys.
- No `git push --force` to `main`/`master`.
- Do not skip hooks unless explicitly asked.
- Ask before destructive git (reset --hard, clean -fdx, rewrite history).
- Conventional commits with the story key when a ticket exists.
- Do not push or deploy without explicit user approval.
