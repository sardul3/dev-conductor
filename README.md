# dev-conductor

Jira REST → spec → tests → TDD → verify → review → `gh pr`. Claude Code plugin plus a Cursor install of the same skills. No Jira or GitHub MCP.

https://github.com/sardul3/dev-conductor

## Install

```bash
git clone https://github.com/sardul3/dev-conductor.git
cd dev-conductor
./install.sh
```

Installs the CLI to `~/.claude/hooks/dev-loop/`, the `/dev-loop` slash command, loop skills and agents, prompt-enrich (spec grill), and the Cursor port (`~/.cursor/skills`, `~/.agents/skills`).

```bash
claude plugin marketplace add /path/to/dev-conductor
```

## Use

```bash
/dev-loop PROJ-123
# or
python3 ~/.claude/hooks/dev-loop/cli.py start PROJ-123 --repo /path/to/repo
```

Config: `~/.config/dev-conductor/dev-loop/config.yaml`  
Secrets: `~/.config/dev-conductor/secrets.env` (`ATLASSIAN_*`). Never commit.

Isolation: `git.isolation: treehouse` leases a worktree (`treehouse get --lease`). Eval uses `none`. Concurrent tickets: `queue.max_active: 3`.

Eval (fake Jira): `python3 dev-loop/cli.py --config dev-loop/config.test.yaml eval --repo /path/to/lab-repo`

## Layout

| Path | Contents |
| ---- | -------- |
| `dev-loop/` | Conductor CLI, config, fake-jira, tests |
| `plugins/dev-loop/` | Claude plugin (`skills` / `agents` / `commands` symlink to sources) |
| `skills/` | Loop + grill skills |
| `claude/agents/` | `code-reviewer`, `debugger`, `code-simplifier` |
| `claude/commands/dev-loop.md` | `/dev-loop` |
| `claude/prompt-enrich/` | Spec grill + launch |
| `cursor/dev-loop/` | Cursor `install.sh` + `dev-loop.mdc` |
| `install.sh` | One-shot install |
| `.envfiles/` | Canonical `AGENTS.md` (root `CLAUDE.md` / `AGENTS.md` are pointers) |

## Tests

```bash
python3 -m unittest discover -s dev-loop/tests -v
python3 -m unittest discover -s claude/prompt-enrich/tests -v
```
