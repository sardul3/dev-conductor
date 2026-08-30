#!/usr/bin/env python3
"""Claude SessionStart hook: print Jira keys only. Fail silent."""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

# Allow running from hooks dir or repo checkout.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import jira_creds, load_config  # noqa: E402
from gitutil import cwd_is_dev_root, denylisted, github_remote, is_git_repo, under_dev  # noqa: E402
from jira_client import search_keys  # noqa: E402
from paths import config_dir  # noqa: E402


def eligible(cwd: Path, cfg) -> bool:
    ss = getattr(cfg, "session_start", None)
    if ss is not None and not getattr(ss, "enabled", True):
        return False
    root = cfg.dev_root.expanduser()
    if cwd_is_dev_root(cwd, root):
        return True
    if not under_dev(cwd, root):
        return False
    if not is_git_repo(cwd):
        return False
    from gitutil import repo_slug
    slug = repo_slug(cwd)
    allow = getattr(cfg, "allowlist", None) or []
    if allow and slug not in allow:
        return False
    if denylisted(cwd, getattr(cfg, "denylist", None) or []):
        return False
    git = getattr(cfg, "git", None)
    require_gh = True if git is None else bool(getattr(git, "require_github_remote", True))
    if require_gh:
        return github_remote(cwd) is not None
    return True


def cache_path() -> Path:
    return config_dir() / "cache" / "keys.json"


def cached_keys(ttl_sec: int) -> list[str] | None:
    p = cache_path()
    if not p.is_file():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    ts = float(data.get("ts") or 0)
    if time.time() - ts > ttl_sec:
        return None
    keys = data.get("keys")
    if not isinstance(keys, list) or not keys:
        return None
    return list(keys)


def store_keys(keys: list[str]) -> None:
    if not keys:
        return
    p = cache_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"ts": time.time(), "keys": keys}) + "\n", encoding="utf-8")


def main() -> int:
    if os.environ.get("DEVLOOP_DISABLE"):
        return 0
    cwd = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
    try:
        cfg = load_config()
    except Exception:
        return 0
    if not eligible(cwd, cfg):
        return 0
    try:
        base, email, token = jira_creds(cfg)
    except SystemExit:
        return 0
    ttl = max(60, int(cfg.session_start.cache_minutes) * 60)
    keys = cached_keys(ttl)
    if keys is None:
        try:
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
        except Exception:
            return 0
    if keys and cfg.session_start.print_keys:
        print("dev-loop Jira keys: " + " ".join(keys[: cfg.session_start.keys_limit]))
        print("Start a ticket: /dev-loop KEY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
