#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from config import DevLoopConfig
from paths import runs_dir
from progress import record

INSTALL_HINT = (
    "install treehouse: curl -fsSL https://kunchenguid.github.io/treehouse/install.sh | sh"
)

DONE = {("ship", "pr"), ("ship", "local"), ("ship", "pushed")}

Runner = Callable[..., Any]


@dataclass(frozen=True)
class Lease:
    path: Path
    lease_id: str
    holder: str = ""
    origin: Path | None = None


def _run(runner: Runner | None) -> Runner:
    return runner or subprocess.run


def is_active_run(run: Path) -> bool:
    status_p = run / "status.json"
    if not status_p.is_file():
        return (run / "lease.json").is_file()
    try:
        data = json.loads(status_p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return (run / "lease.json").is_file()
    if not isinstance(data, dict):
        return False
    cur = data.get("current") if isinstance(data.get("current"), dict) else {}
    stage = str(cur.get("stage") or "")
    status = str(cur.get("status") or "")
    if (stage, status) in DONE:
        return False
    if not stage:
        return (run / "lease.json").is_file()
    return True


def count_active_runs(runs_root: Path, exclude_key: str | None = None) -> int:
    n = 0
    if not runs_root.is_dir():
        return 0
    for child in runs_root.iterdir():
        if not child.is_dir():
            continue
        if exclude_key and child.name.upper() == exclude_key.upper():
            continue
        if is_active_run(child):
            n += 1
    return n


def enforce_capacity(
    cfg: DevLoopConfig,
    runs_root: Path | None = None,
    exclude_key: str | None = None,
) -> None:
    cap = int(cfg.queue.max_active)
    if cap <= 0:
        return
    root = runs_root or runs_dir()
    n = count_active_runs(root, exclude_key=exclude_key)
    if n >= cap:
        raise SystemExit(
            f"dev-loop: {n} active runs (queue.max_active={cap}). "
            "Finish a ticket, or `treehouse return PATH` to free a lease."
        )


def acquire_lease(
    origin: Path,
    *,
    bin: str = "treehouse",
    holder: str = "dev-loop",
    runner: Runner | None = None,
) -> Lease:
    cmd = [bin, "get", "--lease", "--json", "--lease-holder", holder]
    try:
        proc = _run(runner)(cmd, cwd=str(origin), capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise SystemExit(
            f"dev-loop: treehouse binary not found ({bin}). {INSTALL_HINT}"
        ) from exc
    if getattr(proc, "returncode", 0) not in (0, None):
        err = (getattr(proc, "stderr", None) or getattr(proc, "stdout", None) or "").strip()
        raise SystemExit(f"dev-loop: treehouse get --lease failed: {err or 'unknown error'}")
    raw = (getattr(proc, "stdout", None) or "").strip()
    if not raw:
        raise SystemExit("dev-loop: treehouse get --lease printed no path")
    if raw.startswith("{"):
        try:
            data = json.loads(raw.splitlines()[0])
        except json.JSONDecodeError as exc:
            raise SystemExit(f"dev-loop: treehouse lease JSON unreadable: {raw[:200]}") from exc
        path = Path(str(data.get("path") or "")).expanduser()
        if not str(path):
            raise SystemExit("dev-loop: treehouse lease JSON missing path")
        return Lease(
            path=path,
            lease_id=str(data.get("lease_id") or ""),
            holder=str(data.get("lease_holder") or holder),
            origin=origin,
        )
    return Lease(path=Path(raw.splitlines()[0]).expanduser(), lease_id="", holder=holder, origin=origin)


def prepare_workspace(
    origin: Path,
    cfg: DevLoopConfig,
    run: Path,
    *,
    runs_root: Path | None = None,
    runner: Runner | None = None,
) -> Path:
    enforce_capacity(cfg, runs_root=runs_root, exclude_key=run.name)
    isolation = (cfg.git.isolation or "none").strip().lower()
    if isolation != "treehouse":
        return origin
    holder = f"{cfg.git.treehouse_lease_holder}:{run.name}"
    lease = acquire_lease(
        origin,
        bin=cfg.git.treehouse_bin,
        holder=holder,
        runner=runner,
    )
    payload = {
        "path": str(lease.path),
        "lease_id": lease.lease_id,
        "holder": lease.holder,
        "origin": str(origin),
    }
    (run / "lease.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    record(run, "isolation", "leased", ticket=run.name, note=str(lease.path))
    return lease.path


def workspace_for_run(run: Path, origin: Path) -> Path:
    p = run / "lease.json"
    if not p.is_file():
        return origin
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return origin
    if not isinstance(data, dict):
        return origin
    wt = Path(str(data.get("path") or "")).expanduser()
    if str(wt) and wt.exists():
        return wt
    return origin


def release_lease(
    run: Path,
    cfg: DevLoopConfig,
    *,
    runner: Runner | None = None,
) -> None:
    if not cfg.git.treehouse_return_on_ship:
        return
    p = run / "lease.json"
    if not p.is_file():
        return
    isolation = (cfg.git.isolation or "none").strip().lower()
    if isolation != "treehouse":
        return
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return
    if not isinstance(data, dict):
        return
    path = str(data.get("path") or "")
    lease_id = str(data.get("lease_id") or "")
    if not path:
        return
    cmd = [cfg.git.treehouse_bin, "return", "--force"]
    if lease_id:
        cmd.extend(["--if-lease-id", lease_id])
    cmd.append(path)
    try:
        proc = _run(runner)(cmd, capture_output=True, text=True)
    except FileNotFoundError:
        print(f"dev-loop: treehouse missing; lease still held at {path}")
        return
    if getattr(proc, "returncode", 0) not in (0, None):
        err = (getattr(proc, "stderr", None) or getattr(proc, "stdout", None) or "").strip()
        print(f"dev-loop: treehouse return failed ({err}); lease still held at {path}")
        return
    record(run, "isolation", "returned", ticket=run.name, note=path)
