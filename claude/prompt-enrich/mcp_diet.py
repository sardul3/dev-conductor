#!/usr/bin/env python3
"""Move heavy MCPs off user scope so they do not load on every session."""

from __future__ import annotations

import argparse
import json
import shutil
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

HEAVY_SERVERS = ("jira", "identityiq")


def strip_user_servers(config: dict, names: tuple[str, ...] = HEAVY_SERVERS) -> tuple[dict, dict]:
    out = deepcopy(config)
    mcp = dict(out.get("mcpServers") or {})
    extracted: dict = {}
    for name in names:
        if name in mcp:
            extracted[name] = mcp.pop(name)
    out["mcpServers"] = mcp
    return out, extracted


def apply_file(claude_json: Path, backup_dir: Path) -> dict:
    data = json.loads(claude_json.read_text(encoding="utf-8"))
    updated, extracted = strip_user_servers(data)
    if extracted:
        backup_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        shutil.copy2(claude_json, backup_dir / f"claude.json.{stamp}")
        extracted_path = backup_dir / f"mcp-extracted.{stamp}.json"
        extracted_path.write_text(json.dumps(extracted, indent=2) + "\n", encoding="utf-8")
        claude_json.write_text(json.dumps(updated, indent=2) + "\n", encoding="utf-8")
    return extracted


def main() -> int:
    parser = argparse.ArgumentParser(description="Remove Jira/IdentityIQ from user-scoped MCP")
    parser.add_argument("--claude-json", default=str(Path.home() / ".claude.json"))
    parser.add_argument(
        "--backup-dir",
        default=str(Path.home() / ".config" / "dev-conductor" / "backups" / "mcp-diet"),
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    path = Path(args.claude_json)
    data = json.loads(path.read_text(encoding="utf-8"))
    _, extracted = strip_user_servers(data)
    print(json.dumps({"would_remove": sorted(extracted.keys()), "dry_run": args.dry_run}))
    if args.dry_run or not extracted:
        return 0
    apply_file(path, Path(args.backup_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
