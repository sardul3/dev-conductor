#!/usr/bin/env python3
"""Cursor sessionStart: inject open Jira keys. Fail silent."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

_CLI = Path.home() / ".claude" / "hooks" / "dev-loop"
_REPO = Path(__file__).resolve().parents[3] / "dev-loop"
for cand in (_CLI, _REPO):
    if cand.is_dir():
        sys.path.insert(0, str(cand))
        break

from session_start import (  # noqa: E402
    cached_keys,
    cursor_session_output,
    eligible,
    format_keys_line,
    store_keys,
)
from config import jira_creds, load_config  # noqa: E402
from jira_client import search_keys  # noqa: E402


def _cwd(payload: dict) -> Path:
    roots = payload.get("workspace_roots") or payload.get("workspaceRoots") or []
    if isinstance(roots, list) and roots:
        return Path(str(roots[0])).expanduser()
    for key in ("cwd", "workspace_root", "workspaceRoot"):
        if payload.get(key):
            return Path(str(payload[key])).expanduser()
    return Path(os.getcwd())


def main() -> int:
    if os.environ.get("DEVLOOP_DISABLE"):
        return 0
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        payload = {}
    try:
        cfg = load_config()
        cwd = _cwd(payload if isinstance(payload, dict) else {})
        if not eligible(cwd, cfg):
            return 0
        base, email, token = jira_creds(cfg)
        ttl = max(60, int(cfg.session_start.cache_minutes) * 60)
        keys = cached_keys(ttl)
        if keys is None:
            keys = search_keys(
                base,
                email,
                token,
                cfg.jql,
                max_results=cfg.jira.max_keys,
                search_path=cfg.jira.search_path,
                timeout=cfg.jira.timeout_sec,
            )
            store_keys(keys)
        if keys and cfg.session_start.print_keys:
            line = format_keys_line(keys, cfg.session_start.keys_limit)
            print(json.dumps(cursor_session_output(line)))
    except SystemExit:
        return 0
    except Exception:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
