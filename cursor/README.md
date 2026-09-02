# Cursor: install and run `/dev-loop`

This is the **Cursor-first** install. The same CLI is used by Claude Code; this path does not require Claude Code, prompt-enrich, or a 24-hour poll.

Python **3.10+** is required (3.12 is fine). The stock macOS `/usr/bin/python3` is often 3.9 and will fail the installer.

## 1. Prerequisites

1. **Git clone** this repo (or your fork).
2. **Python 3.10+** on `PATH` as `python3`. If `python3 --version` is 3.9:

   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   export PATH="$HOME/.local/bin:$PATH"
   uv python install 3.12
   ln -sfn "$(uv python find 3.12)" "$HOME/.local/bin/python3"
   python3 --version   # 3.12.x
   ```

3. **`gh`** authenticated to GitHub (`gh auth login`). Ticket repos must have a **GitHub remote**.
4. A Jira API token. Create `~/.config/dev-conductor/secrets.env` (never commit this file):

   ```bash
   mkdir -p ~/.config/dev-conductor
   cat > ~/.config/dev-conductor/secrets.env <<'EOF'
   ATLASSIAN_BASE_URL=https://YOUR.atlassian.net
   ATLASSIAN_EMAIL=you@example.com
   ATLASSIAN_API_TOKEN=your-token
   EOF
   chmod 600 ~/.config/dev-conductor/secrets.env
   ```

## 2. Install

From the clone:

```bash
./cursor/dev-loop/install.sh
```

That script:

| Copies | To |
| ------ | -- |
| Conductor CLI (`dev-loop/*.py`, `brief/`) | `~/.claude/hooks/dev-loop/` (shared with Claude) |
| All `skills/*` | `~/.cursor/skills/` and `~/.agents/skills/` |
| `cursor/commands/dev-loop.md` | `~/.cursor/commands/dev-loop.md` |
| Wrapper | `~/.local/bin/dev-loop` |
| `dev-loop.mdc` + `.envfiles/rules/cursor/*.mdc` | `~/.cursor/rules/` |
| `sessionStart` + `beforeReadFile` hooks | `~/.cursor/hooks.json` (merged, not wiped) |
| Example config | `~/.config/dev-conductor/dev-loop/config.yaml` **only if missing**, with `runtime.agent: cursor` |

It also appends `alias dl='dev-loop'` to `~/.zshrc` if that line is not already there, and ensures `~/.local/bin` is on `PATH` in `~/.zshrc`.

Then:

```bash
source ~/.zshrc
which dev-loop
dev-loop --help
```

In Cursor: **Developer: Reload Window**, open **Agent** chat, type `/` and pick **dev-loop**.

Optional stack rules (Java, Python/ML, …): `./.envfiles/install-rules.sh`.

Full product (Claude prompt-enrich + agents **and** this Cursor port): `./install.sh` from the repo root.

## 3. Config

Edit `~/.config/dev-conductor/dev-loop/config.yaml`:

```yaml
jira:
  project: YOURKEY          # prefixes the default JQL
runtime:
  agent: cursor             # one-stage step; never polls 24h
git:
  isolation: worktree       # default
  require_github_remote: true
dev_root: ~/dev             # start --repo must live here unless allow_outside_dev
```

`cli.py keys` only lists issues matching `assignee = currentUser() AND sprint in openSprints() AND statusCategory != Done`. Other tickets still work with `dev-loop start KEY --repo PATH`.

## 4. Daily loop

The repo you pass to `--repo` must be a **git clone with a GitHub remote**, under `~/dev`. A folder with no `origin` will exit: `no GitHub remote`.

```bash
# Agent chat
/dev-loop KEY
# or terminal
dev-loop start KEY --repo ~/dev/your-clone
# alias
dl start KEY --repo ~/dev/your-clone
```

1. Grill the spec **in that chat** (`story-spec`). Do not implement yet.
2. When you accept the spec (not the ticket), the agent writes `SPEC_APPROVED` then:

   ```bash
   dev-loop step KEY
   ```

3. Each `step` is **one** stage (test-writer → writer → verify → review → ship). Write `STAGE_DONE` / `SESSION_DONE`, then `step` again.
4. Test-writer: spawn a **new Agent**. Parent chat does not Read implementation trees.

Handshake files: `~/.config/dev-conductor/dev-loop/runs/KEY/`.

`dev-loop continue KEY` with `runtime.agent: cursor` is the same as `step`. Do not use `continue --no-wait`.

## 5. What install does not do

- Create `secrets.env` or log you into `gh`.
- Clone your product repo or add a GitHub remote.
- Sync `~/.cursor/skills` or `~/.config/dev-conductor` to another laptop (re-run the installer there after `git pull`).
- Open a PR; ship is `dev-loop step` after review.

## 6. Re-install / other machine

```bash
git pull
./cursor/dev-loop/install.sh
# copy secrets.env by hand (1Password); gh auth login
```

Config.yaml is not overwritten if it already exists.

## Tests

```bash
python3 -m unittest discover -s dev-loop/tests -v
```
