# dev-conductor

Jira-to-PR conductor for Claude Code (plugin + hooks + skills + agents) and a Cursor **copy** of the same loop skills.

https://github.com/sardul3/dev-conductor

Not a machine snapshot. SSH, homelab, OpenRouter, Cursor product settings, and path-scoped stack rules live in sibling **`~/dev/mac-ai-setup`**.

## Install

```bash
git clone https://github.com/sardul3/dev-conductor.git
cd dev-conductor
./install.sh
```

Fills `~/.claude/hooks/dev-loop/`, merges SessionStart / PreToolUse, installs loop skills and agents, prompt-enrich (spec grill + launch), and the Cursor port (`~/.cursor/skills` + `~/.agents/skills`).

Config: `~/.config/dev-conductor/dev-loop/config.yaml`  
Secrets: `~/.config/dev-conductor/secrets.env` (`ATLASSIAN_*`). Never commit.

## Use

```bash
/dev-loop PROJ-123
# or
python3 ~/.claude/hooks/dev-loop/cli.py start PROJ-123 --repo ~/dev/your-app
```

Eval (fake Jira): `python3 dev-loop/cli.py --config dev-loop/config.test.yaml eval --repo ~/dev/devloop-lab`

## What ships

| Path | Contents |
| ---- | -------- |
| `dev-loop/` | CLI, config, fake-jira, tests |
| `plugins/dev-loop/` | Claude Code plugin wrapper |
| `skills/` | Loop + prompt-enrich skills (source of truth) |
| `claude/agents/` | `code-reviewer`, `debugger`, `code-simplifier` |
| `claude/commands/dev-loop.md` | Slash command |
| `claude/prompt-enrich/` | Grill + launch (used by spec stage; optional if you only run the CLI) |
| `cursor/dev-loop/` | Cursor copies — do not edit `skills/` only for Cursor |
| `docs/` | Loop and prompt-enrich specs |
| `install.sh` | One-shot install |

Claude plugin: `.claude-plugin/marketplace.json` → `plugins/dev-loop`.

**Not in this repo:** SSH, homelab, IdentityIQ lab, OpenRouter/CCR dumps, Cursor `settings.json`, path-scoped Java/ML/LLM rules.
