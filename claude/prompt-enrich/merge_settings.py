#!/usr/bin/env python3
"""Merge prompt-enrich UserPromptSubmit into Claude settings without wiping other keys."""

from __future__ import annotations

import argparse
import json
from copy import deepcopy
from pathlib import Path


def merge_hook(
    settings: dict,
    event: str,
    command: str,
    matcher: str | None = None,
    timeout: int | None = None,
) -> dict:
    out = deepcopy(settings)
    hooks = dict(out.get("hooks") or {})
    entries = list(hooks.get(event) or [])
    if command in json.dumps(entries):
        if timeout:
            for entry in entries:
                for hook in entry.get("hooks") or []:
                    if isinstance(hook, dict) and hook.get("command") == command:
                        hook["timeout"] = timeout
        hooks[event] = entries
        out["hooks"] = hooks
        return out
    hook_item: dict = {"type": "command", "command": command}
    if timeout:
        hook_item["timeout"] = timeout
    item: dict = {"hooks": [hook_item]}
    if matcher:
        item["matcher"] = matcher
    entries.append(item)
    hooks[event] = entries
    out["hooks"] = hooks
    return out


def merge_user_prompt_submit(settings: dict, classify_cmd: str) -> dict:
    return merge_hook(settings, "UserPromptSubmit", classify_cmd)


def merge_file(settings_path: Path, classify_cmd: str, extra: list[tuple] | None = None) -> dict:
    if settings_path.is_file():
        data = json.loads(settings_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            data = {}
    else:
        data = {}
        settings_path.parent.mkdir(parents=True, exist_ok=True)
    merged = merge_user_prompt_submit(data, classify_cmd)
    for item in extra or []:
        event, command = item[0], item[1]
        matcher = item[2] if len(item) > 2 else None
        timeout = item[3] if len(item) > 3 else None
        merged = merge_hook(merged, event, command, matcher, timeout=timeout)
    settings_path.write_text(json.dumps(merged, indent=2) + "\n", encoding="utf-8")
    return merged


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--settings", default=str(Path.home() / ".claude" / "settings.json"))
    parser.add_argument("--classify", required=True)
    parser.add_argument("--brevity", default="")
    parser.add_argument("--compress", default="")
    parser.add_argument("--plan-guard", default="")
    parser.add_argument("--session-start", default="")
    parser.add_argument("--after-launch", default="")
    parser.add_argument("--classify-timeout", type=int, default=15)
    args = parser.parse_args()
    extra: list[tuple] = []
    if args.brevity:
        extra.append(("UserPromptSubmit", args.brevity, None))
    if args.compress:
        extra.append(("PostToolUse", args.compress, "Bash"))
    if args.plan_guard:
        extra.append(("PreToolUse", args.plan_guard, "*"))
    if args.session_start:
        extra.append(("SessionStart", args.session_start, None))
    if args.after_launch:
        extra.append(("PostToolUse", args.after_launch, "Bash"))
    settings_path = Path(args.settings)
    if settings_path.is_file():
        data = json.loads(settings_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            data = {}
    else:
        data = {}
        settings_path.parent.mkdir(parents=True, exist_ok=True)
    merged = merge_hook(data, "UserPromptSubmit", args.classify, timeout=args.classify_timeout)
    for item in extra:
        event, command = item[0], item[1]
        matcher = item[2] if len(item) > 2 else None
        timeout = item[3] if len(item) > 3 else None
        merged = merge_hook(merged, event, command, matcher, timeout=timeout)
    settings_path.write_text(json.dumps(merged, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
