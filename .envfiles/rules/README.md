# Path-scoped rules

These files are **not** always-on. Claude loads `*.md` with `paths:` when a matching file is in play. Cursor loads `cursor/*.mdc` with `alwaysApply: false` and `globs`.

Do not paste them into root `CLAUDE.md` or Cursor User Rules.

`git.md` has no `paths:` on purpose — it is a snippet for `~/.claude/CLAUDE.md`. The installer skips it.

```bash
.envfiles/install-rules.sh
```

That copies path-scoped `*.md` → `~/.claude/rules/` and `cursor/*.mdc` → `~/.cursor/rules/`.
