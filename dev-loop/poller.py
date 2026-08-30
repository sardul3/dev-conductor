#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any, Callable

from config import DevLoopConfig
from paths import run_dir
from watch import load_watch, remove_watch, upsert_watch


def _checks_failed(pr: dict[str, Any]) -> bool:
    for item in pr.get("statusCheckRollup") or []:
        state = str(item.get("state") or item.get("conclusion") or "").upper()
        if state in {"FAILURE", "ERROR", "CANCELLED", "TIMED_OUT", "ACTION_REQUIRED"}:
            return True
    return False


def _has_human_comment(pr: dict[str, Any], bot_logins: set[str]) -> bool:
    for c in pr.get("comments") or []:
        login = str(((c.get("author") or {}).get("login")) or "").lower()
        if login and login not in bot_logins and (c.get("body") or "").strip():
            return True
    for r in pr.get("reviews") or []:
        if str(r.get("state") or "").upper() == "CHANGES_REQUESTED":
            return True
        body = (r.get("body") or "").strip()
        login = str(((r.get("author") or {}).get("login")) or "").lower()
        if body and login not in bot_logins:
            return True
    return False


def decide(pr: dict[str, Any], auto_merge: bool = False, bot_logins: set[str] | None = None) -> str:
    bots = {b.lower() for b in (bot_logins or set())}
    state = str(pr.get("state") or "").upper()
    if state in {"MERGED", "CLOSED"}:
        return "done"
    if str(pr.get("reviewDecision") or "").upper() == "CHANGES_REQUESTED":
        return "fix"
    if _checks_failed(pr):
        return "fix"
    if _has_human_comment(pr, bots):
        return "fix"
    approved = str(pr.get("reviewDecision") or "").upper() == "APPROVED"
    checks = pr.get("statusCheckRollup") or []
    green = (not checks) or all(
        str(i.get("state") or "").upper() in {"SUCCESS", "NEUTRAL", "SKIPPED"} for i in checks
    )
    if approved and green:
        return "merge" if auto_merge else "alert"
    return "wait"


def apply_policy(action: str, pr: dict[str, Any], cfg: DevLoopConfig, bot_logins: set[str]) -> str:
    if action != "fix":
        return action
    failed = _checks_failed(pr)
    comments = _has_human_comment(pr, bot_logins) or str(pr.get("reviewDecision") or "").upper() == "CHANGES_REQUESTED"
    if failed and cfg.poller.on_checks_failed != "fix" and not comments:
        return "wait"
    if comments and not failed and cfg.poller.on_comments != "fix":
        return "wait"
    return "fix"


def comment_fingerprint(pr: dict[str, Any]) -> str:
    parts: list[str] = []
    for c in pr.get("comments") or []:
        parts.append(str(c.get("body") or ""))
    for r in pr.get("reviews") or []:
        parts.append(str(r.get("state") or "") + ":" + str(r.get("body") or ""))
    for i in pr.get("statusCheckRollup") or []:
        parts.append(str(i.get("name") or "") + ":" + str(i.get("state") or ""))
    parts.append(str(pr.get("reviewDecision") or ""))
    return hashlib.sha256("\n".join(parts).encode()).hexdigest()[:16]


def gh_pr_view(repo: Path, number: int, gh_bin: str = "gh") -> dict[str, Any]:
    fields = "number,state,title,url,reviewDecision,statusCheckRollup,reviews,comments"
    proc = subprocess.run(
        [gh_bin, "pr", "view", str(number), "--json", fields],
        cwd=str(repo),
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout or "gh pr view failed").strip())
    data = json.loads(proc.stdout or "{}")
    return data if isinstance(data, dict) else {}


def gh_pr_merge(repo: Path, number: int, method: str = "squash", gh_bin: str = "gh") -> None:
    flag = {"squash": "--squash", "merge": "--merge", "rebase": "--rebase"}.get(method, "--squash")
    proc = subprocess.run(
        [gh_bin, "pr", "merge", str(number), flag, "--delete-branch"],
        cwd=str(repo),
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout or "gh pr merge failed").strip())


def notify(title: str, body: str) -> None:
    script = "display notification " + json.dumps(body) + " with title " + json.dumps(title)
    subprocess.run(["osascript", "-e", script], capture_output=True, text=True)


def comments_markdown(pr: dict[str, Any]) -> str:
    lines = ["# PR " + str(pr.get("number")) + " " + str(pr.get("title") or ""), ""]
    for c in pr.get("comments") or []:
        login = ((c.get("author") or {}).get("login")) or "unknown"
        lines.append("## comment @" + login + "\n\n" + str(c.get("body") or "") + "\n")
    for r in pr.get("reviews") or []:
        login = ((r.get("author") or {}).get("login")) or "unknown"
        lines.append("## review " + str(r.get("state")) + " @" + login + "\n\n" + str(r.get("body") or "") + "\n")
    return "\n".join(lines)


def poller_plist(label: str, python: str, cli: str, interval_sec: int, log: str) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
        '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
        '<plist version="1.0">\n<dict>\n'
        '  <key>Label</key>\n  <string>' + label + '</string>\n'
        '  <key>ProgramArguments</key>\n  <array>\n'
        '    <string>' + python + '</string>\n'
        '    <string>' + cli + '</string>\n'
        '    <string>poll</string>\n'
        '  </array>\n'
        '  <key>StartInterval</key>\n  <integer>' + str(int(interval_sec)) + '</integer>\n'
        '  <key>RunAtLoad</key>\n  <false/>\n'
        '  <key>StandardOutPath</key>\n  <string>' + log + '</string>\n'
        '  <key>StandardErrorPath</key>\n  <string>' + log + '</string>\n'
        '</dict>\n</plist>\n'
    )


def install_poller(cfg: DevLoopConfig, load: bool | None = None) -> Path:
    label = "com.dev-conductor.devloop-poller"
    dest = Path.home() / "Library" / "LaunchAgents" / (label + ".plist")
    dest.parent.mkdir(parents=True, exist_ok=True)
    python = "/usr/bin/python3"
    cli = str(Path.home() / ".claude" / "hooks" / "dev-loop" / "cli.py")
    if not Path(cli).is_file():
        cli = str(Path(__file__).resolve().parent / "cli.py")
    log = str(Path.home() / "Library" / "Logs" / "devloop-poller.log")
    Path(log).parent.mkdir(parents=True, exist_ok=True)
    interval = max(60, int(cfg.poller.interval_minutes or 30) * 60)
    dest.write_text(poller_plist(label, python, cli, interval, log), encoding="utf-8")
    uid = os.getuid()
    should_load = cfg.poller.enabled if load is None else load
    subprocess.run(["launchctl", "bootout", "gui/" + str(uid) + "/" + label], capture_output=True, text=True)
    subprocess.run(["launchctl", "bootout", "gui/" + str(uid) + "/com.mac-ai-setup.devloop-poller"], capture_output=True, text=True)
    if should_load:
        proc = subprocess.run(
            ["launchctl", "bootstrap", "gui/" + str(uid), str(dest)],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            print("dev-loop: launchctl bootstrap:", (proc.stderr or proc.stdout or "").strip())
        print("dev-loop: poller loaded every " + str(cfg.poller.interval_minutes) + " min -> " + str(dest))
    else:
        print("dev-loop: wrote " + str(dest) + " (poller.enabled is false; not loaded)")
    return dest


ViewFn = Callable[[dict[str, Any]], dict[str, Any]]
MergeFn = Callable[[dict[str, Any]], None]
FixFn = Callable[[dict[str, Any], dict[str, Any]], None]
AlertFn = Callable[[dict[str, Any]], None]
DoneFn = Callable[[dict[str, Any]], None]


def poll_once(
    cfg: DevLoopConfig,
    watches: list[dict[str, Any]] | None = None,
    view_pr: ViewFn | None = None,
    merge_pr: MergeFn | None = None,
    launch_fix: FixFn | None = None,
    alert: AlertFn | None = None,
    on_done: DoneFn | None = None,
    watch_file: Path | None = None,
) -> list[str]:
    items = watches if watches is not None else load_watch(watch_file)
    bots = {b.lower() for b in (cfg.poller.bot_logins or [])}
    actions: list[str] = []
    for item in list(items):
        repo = Path(str(item.get("repo") or ""))
        prn = int(item.get("pr") or 0)
        if not prn:
            continue
        try:
            pr = view_pr(item) if view_pr else gh_pr_view(repo, prn, gh_bin=cfg.git.gh_bin)
        except Exception as exc:
            print("dev-loop: poll #" + str(prn) + " view failed: " + str(exc))
            actions.append("error")
            continue
        action = apply_policy(decide(pr, auto_merge=cfg.poller.auto_merge, bot_logins=bots), pr, cfg, bots)
        fp = comment_fingerprint(pr)
        if action == "fix" and fp and fp == str(item.get("last_fp") or ""):
            action = "wait"
        print("dev-loop: poll PR #" + str(prn) + " -> " + action)
        if action == "fix":
            upsert_watch({**item, "last_fp": fp}, watch_file)
            if launch_fix:
                launch_fix(item, pr)
            else:
                _default_launch_fix(cfg, item, pr)
        elif action == "merge":
            try:
                if merge_pr:
                    merge_pr(item)
                else:
                    gh_pr_merge(repo, prn, method=cfg.poller.merge_method, gh_bin=cfg.git.gh_bin)
                action = "done"
                if on_done:
                    on_done(item)
                else:
                    _default_done(cfg, item)
                remove_watch(prn, str(item.get("repo") or ""), watch_file)
            except Exception as exc:
                print("dev-loop: merge #" + str(prn) + " failed: " + str(exc))
                action = "error"
        elif action == "alert":
            if cfg.poller.notify:
                if alert:
                    alert(item)
                else:
                    notify("dev-loop PR ready", str(item.get("key")) + " PR #" + str(prn) + " is approved and green")
        elif action == "done":
            if on_done:
                on_done(item)
            else:
                _default_done(cfg, item)
            remove_watch(prn, str(item.get("repo") or ""), watch_file)
        actions.append(action)
    return actions


def _default_launch_fix(cfg: DevLoopConfig, item: dict[str, Any], pr: dict[str, Any]) -> None:
    from conductor import launch_prompt
    from prompts import comment_fixer_prompt

    key = str(item.get("key") or "LOCAL")
    repo = Path(str(item.get("repo") or "."))
    run = run_dir(key)
    (run / "pr-comments.md").write_text(comments_markdown(pr), encoding="utf-8")
    prompt = comment_fixer_prompt(key, run, repo, (run / "pr-comments.md").read_text(encoding="utf-8"))
    launch_prompt(prompt, repo, run, "pr-comment-fixer", cfg)


def _default_done(cfg: DevLoopConfig, item: dict[str, Any]) -> None:
    from jira_workflow import progress

    key = str(item.get("key") or "")
    if key:
        progress(cfg, key, "on_merge", "PR #" + str(item.get("pr")) + " merged")
