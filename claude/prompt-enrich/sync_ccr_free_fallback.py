#!/usr/bin/env python3
"""Turn CCR fallback into a free-model chain. Never writes paid OpenRouter ids."""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

from route_model import assert_ccr_free, load_catalog

DB = Path.home() / ".claude-code-router" / "config.sqlite"


def free_chain(catalog: dict | None = None) -> list[str]:
    data = catalog or load_catalog()
    raw = list(data.get("ccr_free_chain") or [])
    if not raw:
        row = (data.get("ccr") or {}).get("code") or {}
        raw = [row.get("primary"), row.get("fallback"), *(row.get("fallbacks") or [])]
    out: list[str] = []
    for item in raw:
        slug = assert_ccr_free(str(item or ""))
        if slug not in out:
            out.append(slug)
    if not out:
        raise SystemExit("no free models in catalog")
    return out


def apply(db_path: Path = DB) -> dict:
    if not db_path.is_file():
        raise SystemExit(f"no CCR db at {db_path} — set Routing → Fallback targets in the CCR UI")
    chain = free_chain()
    con = sqlite3.connect(str(db_path))
    try:
        row = con.execute("SELECT value_json FROM app_config WHERE key = 'default'").fetchone()
        if not row:
            raise SystemExit("CCR app_config.default missing")
        data = json.loads(row[0])
        router = data.setdefault("Router", {})
        router["fallback"] = {"mode": "model-chain", "models": chain, "retryCount": 1}
        con.execute(
            "UPDATE app_config SET value_json = ? WHERE key = 'default'",
            (json.dumps(data, separators=(",", ":")),),
        )
        con.commit()
    finally:
        con.close()
    return {"mode": "model-chain", "models": chain, "retryCount": 1}


def main() -> int:
    result = apply()
    print("CCR fallback", result["mode"])
    for i, model in enumerate(result["models"], 1):
        print(f"  {i}. {model}")
    print("Restart CCR (or reload Routing) so the gateway picks this up.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
