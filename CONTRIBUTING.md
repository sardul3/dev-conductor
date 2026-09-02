# Contributing

PRs against [sardul3/dev-conductor](https://github.com/sardul3/dev-conductor) (`main`). Do not commit `secrets.env`, `.env`, or API tokens.

## Checks

```bash
python3 -m unittest discover -s dev-loop/tests -v
python3 -m unittest discover -s claude/prompt-enrich/tests -v
```

Python 3.10+. Cursor install: `./cursor/dev-loop/install.sh` (see `cursor/README.md`). Full install: `./install.sh`.

Slash command sources: `claude/commands/dev-loop.md` (Claude Code) and `cursor/commands/dev-loop.md` (Cursor Agent `/`). Skills: `skills/`.
