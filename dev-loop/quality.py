#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Any

from verify_infer import run_cmd

SEVERITY = {"none": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}


def parse_pit_killed_pct(text: str) -> float | None:
    m = re.search(r"Killed\s+\d+\s+\((\d+(?:\.\d+)?)%\)", text, re.I)
    if m:
        return float(m.group(1))
    m = re.search(r"Mutation Coverage[:\s]+(\d+(?:\.\d+)?)%", text, re.I)
    if m:
        return float(m.group(1))
    m = re.search(r"(\d+(?:\.\d+)?)%\s+killed", text, re.I)
    if m:
        return float(m.group(1))
    return None


def parse_snyk_ok(raw: str, fail_on: str = "high") -> bool:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        low = raw.lower()
        return "no direct-dependency vulnerabilities" in low or (
            "tested " in raw and "found 0" in low
        )
    if data.get("ok") is True:
        return True
    threshold = SEVERITY.get(fail_on.lower(), 3)
    for v in data.get("vulnerabilities") or []:
        sev = str(v.get("severity") or "").lower()
        if SEVERITY.get(sev, 0) >= threshold:
            return False
    return True


def gate_result(kind: str, value: float | None, min_pct: float, metric: str = "killed") -> tuple[bool, str]:
    if value is None:
        return False, f"{kind}: could not parse score"
    if metric == "survived":
        ok = value <= min_pct
        return ok, f"{kind} survived {value}% (max {min_pct}%)"
    ok = value >= min_pct
    return ok, f"{kind} killed {value}% (min {min_pct}%)"


def _cmd_exists(cmd: list[str]) -> bool:
    if not cmd:
        return False
    exe = cmd[0]
    if exe.startswith(".") or "/" in exe:
        return Path(exe).exists()
    return shutil.which(exe) is not None


def _missing(name: str, required: bool, log_chunks: list[str]) -> int:
    msg = f"{name}: binary missing"
    log_chunks.append(msg)
    print(msg)
    return 1 if required else 0


def run_quality(repo: Path, cfg: Any, log_chunks: list[str]) -> int:
    q = getattr(cfg, "quality", None)
    if q is None:
        return 0
    timeout = int(getattr(cfg, "verify_timeout_sec", 1800) or 1800)

    snyk = q.snyk
    if snyk.enabled:
        cmd = (snyk.cmd or "snyk test --json").split()
        if not _cmd_exists(cmd):
            rc = _missing("snyk", snyk.required, log_chunks)
            if rc:
                return rc
        else:
            rc, out = run_cmd(repo, cmd, timeout=timeout)
            log_chunks.append(f"$ {' '.join(cmd)}\nexit {rc}\n{out}")
            if not parse_snyk_ok(out, fail_on=snyk.fail_on):
                print("snyk: quality gate failed")
                return 1

    sonar = q.sonar
    if sonar.enabled:
        cmd = (sonar.cmd or "sonar-scanner").split()
        if not _cmd_exists(cmd):
            rc = _missing("sonar", sonar.required, log_chunks)
            if rc:
                return rc
        else:
            rc, out = run_cmd(repo, cmd, timeout=timeout)
            log_chunks.append(f"$ {' '.join(cmd)}\nexit {rc}\n{out}")
            if rc != 0:
                print("sonar: quality gate failed")
                return 1

    mut = q.mutation
    if mut.enabled:
        cmd = (mut.cmd or "").split()
        if not cmd:
            if (repo / "gradlew").is_file():
                cmd = [str((repo / "gradlew").resolve()), "pitest"]
            elif (repo / "pom.xml").is_file():
                mvn = str(repo / "mvnw") if (repo / "mvnw").is_file() else "mvn"
                cmd = [mvn, "-q", "org.pitest:pitest-maven:mutationCoverage"]
        if not cmd or not _cmd_exists(cmd):
            rc = _missing("mutation", mut.required, log_chunks)
            if rc:
                return rc
        else:
            rc, out = run_cmd(repo, cmd, timeout=timeout)
            log_chunks.append(f"$ {' '.join(cmd)}\nexit {rc}\n{out}")
            killed = parse_pit_killed_pct(out)
            if mut.metric == "survived":
                value = None if killed is None else 100.0 - killed
            else:
                value = killed
            ok, msg = gate_result("mutation", value, float(mut.min_pct), metric=mut.metric)
            log_chunks.append(msg)
            if not ok:
                print(msg)
                return 1
            if rc != 0 and mut.required:
                return 1
    return 0
