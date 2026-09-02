# Installation and first run

This folder is the source of truth: `skills/arch-studio/` in [dev-conductor](https://github.com/sardul3/dev-conductor). Do not copy it by hand into `~/.cursor/skills` on a machine that already uses the Cursor installer.

## Cursor (this branch)

From the clone:

```bash
./cursor/dev-loop/install.sh
```

That copies every `skills/*` folder (including this one) to `~/.cursor/skills/` and `~/.agents/skills/`. Reload the Cursor window, then invoke `/arch-studio` or ask for a system integration / architecture pack.

Discovery uses `design-tree-interview` (alias `grill-deep-ask`). This package does not bundle or impersonate those skills.

## Claude Code

```bash
./claude/prompt-enrich/install-skills.sh
```

That copies to `~/.claude/skills/arch-studio/`. Run `/skills` and confirm `arch-studio` is listed.

## Verify the package

From this skill folder:

```bash
python3 scripts/arch_studio.py doctor
python3 scripts/arch_studio.py validate examples/retail-order-integration.arch.json
python3 scripts/arch_studio.py build examples/retail-order-integration.arch.json --out examples/generated --strict
python3 -m unittest discover -s tests -v
```

Open `examples/generated/review.html` in a browser and the generated `.drawio` file in diagrams.net or draw.io.

## Optional interactive session bridge

```bash
python3 scripts/arch_studio.py serve my-system.arch.json \
  --out architecture-review \
  --claude-bridge \
  --claude-session <session-id-or-name> \
  --open
```

Omit `--claude-session` to create a dedicated bridge session. Omit `--claude-bridge` for a review server that persists decisions but cannot call Claude. The chat bridge needs the `claude` CLI; Cursor-only machines can still serve `review.html`.
