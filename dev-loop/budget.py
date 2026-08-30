#!/usr/bin/env python3
"""Ticket-wide stop caps for long runs. 0 on a field means unlimited."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class BudgetExhausted(Exception):
    pass


def approx_tokens(text: str) -> int:
    return max(1, len(text or "") // 4)


def _now(now: datetime | None) -> datetime:
    if now is None:
        return datetime.now(timezone.utc)
    if now.tzinfo is None:
        return now.replace(tzinfo=timezone.utc)
    return now.astimezone(timezone.utc)


def _iso(now: datetime) -> str:
    return _now(now).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_iso(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.strptime(raw, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def caps_active(cfg) -> bool:
    c = getattr(cfg, "caps", None)
    if c is None:
        return False
    return any(
        [
            int(getattr(c, "max_launches", 0) or 0) > 0,
            int(getattr(c, "max_tokens", 0) or 0) > 0,
            float(getattr(c, "max_budget_usd", 0) or 0) > 0,
            int(getattr(c, "wall_sec", 0) or 0) > 0,
        ]
    )


def counts_against_budget(cfg) -> bool:
    rt = getattr(cfg, "runtime", None)
    if rt is None:
        return False
    if bool(getattr(rt, "no_launch", False)):
        return False
    if str(getattr(rt, "agent", "") or "") == "none":
        return False
    return caps_active(cfg)


def load_budget(run: Path) -> dict[str, Any]:
    p = Path(run) / "budget.json"
    data: dict[str, Any] = {
        "launches": 0,
        "tokens": 0,
        "usd": 0.0,
        "started_at": None,
        "events": [],
    }
    if p.is_file():
        try:
            loaded = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            loaded = {}
        if isinstance(loaded, dict):
            data.update(loaded)
    data["launches"] = int(data.get("launches") or 0)
    data["tokens"] = int(data.get("tokens") or 0)
    data["usd"] = float(data.get("usd") or 0)
    data["events"] = list(data.get("events") or [])
    return data


def save_budget(run: Path, data: dict[str, Any]) -> None:
    Path(run).mkdir(parents=True, exist_ok=True)
    (Path(run) / "budget.json").write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def remaining_session_usd(cfg, run: Path) -> float | None:
    cap = float(getattr(getattr(cfg, "caps", None), "max_budget_usd", 0) or 0)
    if cap <= 0:
        return None
    spent = float(load_budget(run).get("usd") or 0)
    return max(0.0, round(cap - spent, 4))


def check_budget(
    cfg,
    run: Path,
    *,
    now: datetime | None = None,
    extra_tokens: int = 0,
    extra_usd: float = 0.0,
) -> tuple[bool, str]:
    if not caps_active(cfg):
        return True, "unlimited"
    data = load_budget(run)
    caps = cfg.caps
    wall = int(getattr(caps, "wall_sec", 0) or 0)
    started = _parse_iso(data.get("started_at"))
    stamp = _now(now)
    if wall > 0 and started is not None:
        elapsed = (stamp - started).total_seconds()
        if elapsed >= wall:
            return False, f"wall {int(elapsed)}s >= {wall}s"
    launches_cap = int(getattr(caps, "max_launches", 0) or 0)
    if launches_cap > 0 and int(data["launches"]) >= launches_cap:
        return False, f"launches {data['launches']} >= {launches_cap}"
    tokens_cap = int(getattr(caps, "max_tokens", 0) or 0)
    next_tokens = int(data["tokens"]) + int(extra_tokens)
    if tokens_cap > 0 and next_tokens > tokens_cap:
        return False, f"tokens {next_tokens} > {tokens_cap}"
    usd_cap = float(getattr(caps, "max_budget_usd", 0) or 0)
    next_usd = float(data["usd"]) + float(extra_usd)
    if usd_cap > 0 and next_usd > usd_cap:
        return False, f"usd {next_usd} > {usd_cap}"
    remaining = remaining_session_usd(cfg, run)
    if remaining is not None and remaining <= 0:
        return False, "usd remaining 0"
    return True, "ok"


def check_and_charge(
    cfg,
    run: Path,
    *,
    prompt: str = "",
    name: str = "",
    now: datetime | None = None,
    tokens: int | None = None,
    usd: float = 0.0,
) -> dict[str, Any]:
    add = int(tokens) if tokens is not None else approx_tokens(prompt)
    ok, reason = check_budget(cfg, run, now=now, extra_tokens=add, extra_usd=usd)
    if not ok:
        raise BudgetExhausted(reason)
    data = load_budget(run)
    stamp = _now(now)
    if not data.get("started_at"):
        data["started_at"] = _iso(stamp)
    data["launches"] = int(data["launches"]) + 1
    data["tokens"] = int(data["tokens"]) + add
    data["usd"] = float(data["usd"]) + float(usd)
    data["events"].append({"at": _iso(stamp), "name": name, "tokens": add, "usd": float(usd)})
    save_budget(run, data)
    return data


def add_usage(run: Path, *, tokens: int = 0, usd: float = 0.0, now: datetime | None = None) -> dict[str, Any]:
    data = load_budget(run)
    stamp = _now(now)
    if not data.get("started_at"):
        data["started_at"] = _iso(stamp)
    data["tokens"] = int(data["tokens"]) + int(tokens)
    data["usd"] = float(data["usd"]) + float(usd)
    data["events"].append({"at": _iso(stamp), "name": "usage", "tokens": int(tokens), "usd": float(usd)})
    save_budget(run, data)
    return data


def stop_run(cfg, run: Path, reason: str) -> None:
    Path(run).mkdir(parents=True, exist_ok=True)
    (Path(run) / "STOPPED").write_text(reason.rstrip() + "\n", encoding="utf-8")
    try:
        from progress import record

        record(run, "budget", "exhausted", ticket=Path(run).name, note=reason)
    except Exception:
        pass
    try:
        from jira_workflow import progress

        progress(cfg, Path(run).name, "on_block", f"budget: {reason}")
    except Exception:
        pass
