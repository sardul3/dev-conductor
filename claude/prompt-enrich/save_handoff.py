#!/usr/bin/env python3
"""Write a prompt-enrich handoff under ~/.claude/prompt-enrichment/runs (not /tmp).

Claude Code's Write tool is sandboxed to the project, so /tmp writes get rejected.
This helper is meant to be called from Bash with the markdown on stdin.
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

SKIP_MARKER = "<!-- PROMPT_CONTRACT_V1 -->"


def save_handoff(text: str, runs_dir: Path, now_utc: str | None = None) -> Path:
    runs_dir.mkdir(parents=True, exist_ok=True)
    stamp = (now_utc or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")).replace(":", "-")
    path = runs_dir / f"handoff-{stamp}.md"
    body = text.strip() + "\n"
    if SKIP_MARKER not in body:
        body = f"{SKIP_MARKER}\n{body}"
    elif not body.lstrip().startswith(SKIP_MARKER):
        body = f"{SKIP_MARKER}\n{body}"
    path.write_text(body, encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--runs-dir",
        default=os.environ.get(
            "PROMPT_ENRICH_RUNS_DIR",
            str(Path.home() / ".claude" / "prompt-enrichment" / "runs"),
        ),
    )
    args = parser.parse_args()
    text = sys.stdin.read()
    if not text.strip():
        print("empty handoff on stdin", file=sys.stderr)
        return 1
    path = save_handoff(text, Path(args.runs_dir))
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
