# dev-conductor

Jira REST → spec → tests → TDD → verify → review → `gh pr`. Claude Code plugin plus a Cursor install of the same skills. No Jira or GitHub MCP.

https://github.com/sardul3/dev-conductor

## Install

**Cursor (Agent `/dev-loop`, stepper CLI):** follow **[cursor/README.md](cursor/README.md)** (`./cursor/dev-loop/install.sh`).

**Claude Code + Cursor together:**

```bash
git clone https://github.com/sardul3/dev-conductor.git
cd dev-conductor
./install.sh
```

Installs the CLI to `~/.claude/hooks/dev-loop/`, `/dev-loop` for Claude Code, loop skills and agents, prompt-enrich, and the Cursor port (`~/.cursor/skills`, `~/.local/bin/dev-loop`). How to send a PR: [CONTRIBUTING.md](CONTRIBUTING.md).

Optional path-scoped stack rules (Java, Python/ML, LLM, TypeScript, k8s, …) live in `.envfiles/rules/` and are **not** always-on:

```bash
./.envfiles/install-rules.sh
```

```bash
claude plugin marketplace add /path/to/dev-conductor
```

## Use

```bash
/dev-loop PROJ-123
# or
dev-loop start PROJ-123 --repo /path/to/repo
```

Config: `~/.config/dev-conductor/dev-loop/config.yaml`  
Secrets: `~/.config/dev-conductor/secrets.env` (`ATLASSIAN_*`). Never commit.

Isolation: `git.isolation: worktree` (default) uses native `git worktree` under `{repo}-worktrees/{KEY}` (visible sibling of the clone). `treehouse` remains opt-in. Eval uses `none`. Concurrent tickets: `queue.max_active: 3`.

Eval (fake Jira): `python3 dev-loop/cli.py --config dev-loop/config.test.yaml eval --repo /path/to/lab-repo`

## Layout

| Path | Contents |
| ---- | -------- |
| `dev-loop/` | Conductor CLI, config, fake-jira, tests |
| `plugins/dev-loop/` | Claude plugin (`skills` / `agents` / `commands` symlink to sources) |
| `skills/` | Loop + grill skills |
| `claude/agents/` | `code-reviewer`, `debugger`, `code-simplifier` |
| `cursor/README.md` | Cursor install, `/dev-loop`, `dev-loop` CLI |
| `cursor/dev-loop/` | Cursor `install.sh`, hooks, `dev-loop.mdc` |
| `cursor/commands/dev-loop.md` | Cursor Agent `/dev-loop` |
| `claude/commands/dev-loop.md` | Claude Code `/dev-loop` |
| `claude/prompt-enrich/` | Spec grill + launch |
| `install.sh` | One-shot Claude + Cursor install |
| `.envfiles/` | Canonical `AGENTS.md` / `CLAUDE.md` plus path-scoped `rules/` |

## Tests

```bash
python3 -m unittest discover -s dev-loop/tests -v
python3 -m unittest discover -s claude/prompt-enrich/tests -v
```
