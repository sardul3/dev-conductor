#!/usr/bin/env python3
"""PreToolUse: while test-writer stage, deny Read/Grep/Glob of implementation sources."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from state import load_state  # noqa: E402

BLOCK_TOOLS = {"Read", "Grep", "Glob"}
IMPL = re.compile(
    r"(src/main/|src/main\\|/lib/|/internal/|app/src/main/)",
    re.I,
)
TEST_OK = re.compile(
    r"(src/test/|/tests/|__tests__|/test/|spec/)",
    re.I,
)
CONTRACT_OK = re.compile(
    r"(openapi|swagger|\.proto$|contracts\.md$)",
    re.I,
)


def _blob(payload: dict) -> str:
    inp = payload.get("tool_input") or payload.get("toolInput") or {}
    parts = [
        str(inp.get("path") or inp.get("file_path") or inp.get("target_directory") or ""),
        str(inp.get("pattern") or inp.get("glob") or ""),
        json.dumps(inp, default=str),
    ]
    return " ".join(parts)


def should_deny(payload: dict, stage: str | None) -> bool:
    if stage != "test-writer":
        return False
    name = str(payload.get("tool_name") or payload.get("toolName") or "")
    if name not in BLOCK_TOOLS:
        return False
    blob = _blob(payload)
    if TEST_OK.search(blob) or CONTRACT_OK.search(blob):
        return False
    if IMPL.search(blob):
        return True
    # Glob/Grep over the whole repo during test-writer is an explore of impl.
    if name in {"Glob", "Grep"} and not TEST_OK.search(blob):
        return True
    return False


def main() -> int:
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        return 0
    stage = str(load_state().get("stage") or "")
    if should_deny(payload, stage):
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "deny",
                        "permissionDecisionReason": (
                            "test-writer: do not Read implementation sources. "
                            "Use spec.md + contracts.md + test paths only."
                        ),
                    }
                }
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
