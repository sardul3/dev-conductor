#!/usr/bin/env python3
"""Merge Cursor user hooks.json without wiping unrelated hooks."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def merge_devloop_hooks(data: dict, session_cmd: str, deny_cmd: str) -> dict:
    out = dict(data) if isinstance(data, dict) else {}
    out["version"] = int(out.get("version") or 1)
    hooks = dict(out.get("hooks") or {}) if isinstance(out.get("hooks"), dict) else {}

    def upsert(event: str, command: str, matcher: str | None = None) -> None:
        entries = list(hooks.get(event) or []) if isinstance(hooks.get(event), list) else []
        marker = "dev-loop/" in command or "session_start_cursor" in command or "deny_read_cursor" in command
        kept = []
        for item in entries:
            if not isinstance(item, dict):
                kept.append(item)
                continue
            cmd = str(item.get("command") or "")
            if "session_start_cursor" in cmd or "deny_read_cursor" in cmd or "hooks/dev-loop" in cmd:
                continue
            kept.append(item)
        rec: dict = {"command": command}
        if matcher:
            rec["matcher"] = matcher
        if marker:
            kept.append(rec)
        else:
            kept.append(rec)
        hooks[event] = kept

    upsert("sessionStart", session_cmd)
    upsert("beforeReadFile", deny_cmd)
    upsert("preToolUse", deny_cmd, matcher="Read|Grep|Glob")
    out["hooks"] = hooks
    return out


def main() -> int:
    dest = Path(sys.argv[1]).expanduser()
    session_cmd = sys.argv[2]
    deny_cmd = sys.argv[3]
    data: dict = {}
    if dest.is_file():
        try:
            parsed = json.loads(dest.read_text(encoding="utf-8"))
            if isinstance(parsed, dict):
                data = parsed
        except json.JSONDecodeError:
            data = {}
    dest.parent.mkdir(parents=True, exist_ok=True)
    merged = merge_devloop_hooks(data, session_cmd, deny_cmd)
    dest.write_text(json.dumps(merged, indent=2) + "\n", encoding="utf-8")
    print("merged Cursor hooks into", dest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
