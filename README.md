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
python3 ~/.claude/hooks/dev-loop/cli.py start PROJ-123 --repo /path/to/repo
```

Config: `~/.config/dev-conductor/dev-loop/config.yaml`  
Secrets: `~/.config/dev-conductor/secrets.env` (`ATLASSIAN_*`). Never commit.

Isolation: `git.isolation: worktree` (default) uses native `git worktree` under `.{repo}-worktrees/{KEY}`. `treehouse` remains opt-in. Eval uses `none`. Concurrent tickets: `queue.max_active: 3`.

Eval (fake Jira): `python3 dev-loop/cli.py --config dev-loop/config.test.yaml eval --repo /path/to/lab-repo`

Pre-production gates (static, ordered tests, boot smoke, new CVEs, artifact bundle) run inside `verify` before a PR. Risk class is `safe`, `normal`, or `sensitive` in config. Deploy, release, and post-release stay after merge.

```bash
python3 dev-loop/cli.py verify --repo /path/to/repo
```

The run dir then has `verify.log`, `verify-result.json` (`pr_allowed`), and `verify-bundle/`. A sensitive ticket also needs a person's name in `HUMAN_APPROVED` and threat-model plus pen-test sections in the spec. PIT floor starts at 75% killed, on the diff only.

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
| `.envfiles/` | Canonical `AGENTS.md` / `CLAUDE.md` plus path-scoped `rules/` |

## Tests

```bash
python3 -m unittest discover -s dev-loop/tests -v
python3 -m unittest discover -s claude/prompt-enrich/tests -v
```
