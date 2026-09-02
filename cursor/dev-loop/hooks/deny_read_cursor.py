#!/usr/bin/env python3
"""Cursor beforeReadFile / preToolUse: deny impl reads during test-writer."""

from __future__ import annotations

import json
import sys
from pathlib import Path

_CLI = Path.home() / ".claude" / "hooks" / "dev-loop"
_REPO = Path(__file__).resolve().parents[3] / "dev-loop"
for cand in (_CLI, _REPO):
    if cand.is_dir():
        sys.path.insert(0, str(cand))
        break

from deny_impl import cursor_decision  # noqa: E402
from state import load_state  # noqa: E402


def main() -> int:
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        return 0
    stage = str(load_state().get("stage") or "")
    out = cursor_decision(payload if isinstance(payload, dict) else {}, stage)
    if out.get("permission") == "deny":
        print(json.dumps(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
