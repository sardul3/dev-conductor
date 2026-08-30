#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import threading
from pathlib import Path

from conductor import start
from config import DevLoopConfig
from fake_jira import serve
from gitutil import current_branch, run_git
from jira_client import search_keys
from paths import run_dir

KEYS = ["LAB-1", "LAB-2", "LAB-3", "LAB-4", "LAB-5"]


def ensure_lab_repo(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    if not (path / ".git").exists():
        subprocess.check_call(["git", "init", "-b", "main"], cwd=path, stdout=subprocess.DEVNULL)
        subprocess.check_call(["git", "config", "user.email", "eval@local"], cwd=path)
        subprocess.check_call(["git", "config", "user.name", "eval"], cwd=path)
        (path / "README.md").write_text("# devloop-lab\nGreenfield task API for dev-loop eval.\n", encoding="utf-8")
        subprocess.check_call(["git", "add", "README.md"], cwd=path)
        subprocess.check_call(["git", "commit", "-m", "chore: init lab"], cwd=path, stdout=subprocess.DEVNULL)
    return path


def run_eval(cfg: DevLoopConfig, repo: Path | None) -> int:
    lab = repo or (cfg.dev_root.expanduser() / "devloop-lab")
    ensure_lab_repo(lab)
    httpd = serve("127.0.0.1", 8765)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    results = []
    proc = None
    tests_ok = False
    try:
        keys = search_keys(
            cfg.jira.base_url,
            "eval@local",
            "none",
            cfg.jql,
            max_results=cfg.jira.max_keys,
            search_path=cfg.jira.search_path,
            timeout=cfg.jira.timeout_sec,
        )
        print("eval keys from fake jira:", keys)
        for key in KEYS:
            try:
                start(key, lab, cfg)
                run = run_dir(key)
                ok = (run / "spec.md").is_file() and (run / "APPROVED").is_file() and (run / "verdict.json").is_file()
                results.append({"key": key, "ok": ok, "error": None})
            except Exception as exc:
                results.append({"key": key, "ok": False, "error": str(exc)})
        proc = subprocess.run(
            ["python3", "-m", "unittest", "discover", "-s", "tests", "-q"],
            cwd=lab,
            capture_output=True,
            text=True,
        )
        tests_ok = proc.returncode == 0
        print(proc.stdout or "")
        print(proc.stderr or "")
    finally:
        httpd.shutdown()
    passed = sum(1 for r in results if r["ok"])
    report = {
        "stories": results,
        "stories_ok": passed,
        "stories_n": len(KEYS),
        "unittest_ok": tests_ok,
        "unittest_log": ((proc.stderr if proc else "") or "")[-2000:],
        "lab": str(lab),
        "head": run_git(lab, "log", "-1", "--oneline"),
        "branch": current_branch(lab),
    }
    out = lab / "eval-report.json"
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    if passed == len(KEYS) and tests_ok:
        print("eval: PASS")
        return 0
    print("eval: FAIL")
    return 1
