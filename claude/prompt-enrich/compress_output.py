#!/usr/bin/env python3
"""PostToolUse: replace huge test/build logs with failures-only before Claude sees them."""

from __future__ import annotations

import json
import os
import re
import sys

MIN_LINES = 80
KEEP_MAX = 120
FAIL_LINE = re.compile(
    r"(FAILED|FAILURE|ERROR|AssertionError|E\s+|Caused by:|failures?=|BUILD FAILED|"
    r"FAILED tests/|✖|● )",
    re.I,
)
SUMMARY = re.compile(r"(passed|failed|error|skipped|FAILURES|====)", re.I)
TESTISH = re.compile(
    r"\b(pytest|py.test|gradlew|gradle|mvn |npm test|pnpm test|yarn test|jest|"
    r"go test|cargo test|phpunit|ctest|rake test|./gradlew)\b",
    re.I,
)


def _stdout(payload: dict) -> str:
    resp = payload.get("tool_response")
    if isinstance(resp, str):
        return resp
    if isinstance(resp, dict):
        for key in ("stdout", "output", "content"):
            val = resp.get(key)
            if isinstance(val, str) and val:
                return val
            if isinstance(val, list):
                parts = []
                for item in val:
                    if isinstance(item, dict) and item.get("text"):
                        parts.append(str(item["text"]))
                    elif isinstance(item, str):
                        parts.append(item)
                if parts:
                    return "\n".join(parts)
    return ""


def compress_text(command: str, text: str) -> str | None:
    if os.environ.get("PROMPT_ENRICH_DISABLE") == "1":
        return None
    lines = text.splitlines()
    if len(lines) < MIN_LINES:
        return None
    testish = bool(TESTISH.search(command or "")) or any(FAIL_LINE.search(ln) for ln in lines)
    if not testish:
        return None
    kept: list[str] = []
    for line in lines:
        if FAIL_LINE.search(line) or (SUMMARY.search(line) and ("fail" in line.lower() or "error" in line.lower() or "==" in line)):
            kept.append(line)
    if not kept:
        kept = lines[-40:]
    kept = kept[:KEEP_MAX]
    header = f"[compressed {len(lines)} lines → {len(kept)} failure/summary lines]"
    return header + "\n" + "\n".join(kept) + "\n"


def compress_payload(payload: dict) -> dict | None:
    name = str(payload.get("tool_name") or payload.get("toolName") or "")
    if name != "Bash":
        return None
    cmd = ""
    tool_input = payload.get("tool_input") or payload.get("toolInput") or {}
    if isinstance(tool_input, dict):
        cmd = str(tool_input.get("command") or "")
    text = _stdout(payload)
    compressed = compress_text(cmd, text)
    if not compressed:
        return None
    return {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "updatedToolOutput": compressed,
        }
    }


def main() -> int:
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw) if raw.strip() else {}
        result = compress_payload(payload)
        if result:
            print(json.dumps(result))
    except Exception:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
