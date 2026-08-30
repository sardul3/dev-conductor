#!/usr/bin/env python3
"""dev-loop CLI. After install: python3 ~/.claude/hooks/dev-loop/cli.py"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import example_yaml, load_config  # noqa: E402
from conductor import continue_loop, fetch_issue, require_key, require_repo, start  # noqa: E402
from memory import index_is_fresh, load_or_build  # noqa: E402
from paths import config_dir, run_dir, state_path  # noqa: E402
from session_start import main as session_start_main  # noqa: E402
from state import load_state  # noqa: E402
from verify_infer import infer_recipe, run_verify  # noqa: E402


def cmd_keys(_: argparse.Namespace) -> int:
    return session_start_main()


def _cfg(ns: argparse.Namespace):
    path = getattr(ns, "config", None)
    return load_config(Path(path).expanduser() if path else None)


def cmd_start(ns: argparse.Namespace) -> int:
    from pick import resolve_repo

    cfg = _cfg(ns)
    repo = resolve_repo(cfg, ns.repo, require=None)
    start(ns.key, repo, cfg)
    return 0


def cmd_continue(ns: argparse.Namespace) -> int:
    from pick import resolve_repo

    cfg = _cfg(ns)
    if ns.repo:
        repo = resolve_repo(cfg, ns.repo, require=None)
    else:
        st = load_state()
        repo = Path(st["repo"]).expanduser() if st.get("repo") else resolve_repo(cfg, None, require=None)
    wait = not ns.no_wait
    return continue_loop(ns.key, repo, cfg, wait=wait)


def cmd_repos(ns: argparse.Namespace) -> int:
    from pick import candidates_payload

    print(json.dumps(candidates_payload(_cfg(ns)), indent=2))
    return 0


def cmd_init_repo(ns: argparse.Namespace) -> int:
    from pick import init_repo

    dest = init_repo(_cfg(ns), ns.name)
    print(dest)
    return 0


def cmd_fetch(ns: argparse.Namespace) -> int:
    dest = fetch_issue(require_key(ns.key), _cfg(ns))
    print(dest / "issue.json")
    return 0


def cmd_memory(ns: argparse.Namespace) -> int:
    cfg = _cfg(ns)
    repo = Path(ns.repo).expanduser().resolve() if ns.repo else Path.cwd()
    repo = require_repo(repo, cfg)
    if ns.force:
        from memory import regenerate

        mem = regenerate(repo)
        print(f"regenerated {mem}")
        return 0
    mem = load_or_build(repo)
    print(mem)
    print("fresh" if index_is_fresh(repo) else "rebuilt")
    return 0


def cmd_verify(ns: argparse.Namespace) -> int:
    cfg = _cfg(ns)
    repo = Path(ns.repo).expanduser().resolve() if ns.repo else Path.cwd()
    repo = require_repo(repo, cfg)
    key = ns.key or load_state().get("ticket") or "LOCAL"
    log = run_dir(str(key)) / "verify.log"
    return run_verify(repo, cfg, log)


def cmd_status(_: argparse.Namespace) -> int:
    from paths import run_dir
    from progress import backfill, render_progress, load_status

    st = load_state()
    print(json.dumps(st, indent=2))
    print("config", config_dir() / "config.yaml")
    print("state", state_path())
    key = st.get("ticket")
    if key:
        run = run_dir(str(key))
        if run.is_dir():
            backfill(run)
            data = load_status(run)
            print()
            print(render_progress(str(key), data.get("current"), list(data.get("history") or [])))
    return 0


def cmd_progress(ns: argparse.Namespace) -> int:
    from progress import backfill

    key = ns.key or load_state().get("ticket")
    if not key:
        print("dev-loop: no ticket — pass KEY or start a loop first")
        return 2
    run = run_dir(str(key))
    if not run.is_dir():
        print(f"dev-loop: no run dir {run}")
        return 2
    backfill(run)
    print((run / "progress.md").read_text(encoding="utf-8"))
    return 0


def cmd_infer(ns: argparse.Namespace) -> int:
    cfg = _cfg(ns)
    repo = Path(ns.repo).expanduser().resolve() if ns.repo else Path.cwd()
    r = infer_recipe(repo, cfg)
    if r is None:
        print("cannot infer")
        return 2
    print("test", " ".join(r.test))
    print("build", " ".join(r.build))
    print("health", r.health or "")
    return 0


def cmd_print_example(_: argparse.Namespace) -> int:
    print(example_yaml())
    return 0


def cmd_eval(ns: argparse.Namespace) -> int:
    from eval_harness import run_eval
    return run_eval(_cfg(ns), Path(ns.repo).expanduser() if ns.repo else None)


def cmd_poll(ns: argparse.Namespace) -> int:
    from poller import poll_once

    actions = poll_once(_cfg(ns))
    print("poll", " ".join(actions) if actions else "(no watched PRs)")
    return 0


def cmd_install_poller(ns: argparse.Namespace) -> int:
    from poller import install_poller

    dest = install_poller(_cfg(ns), load=None if ns.load is None else bool(ns.load))
    print(dest)
    return 0


def cmd_jira_progress(ns: argparse.Namespace) -> int:
    from jira_workflow import progress

    cfg = _cfg(ns)
    key = require_key(ns.key)
    progress(cfg, key, ns.event, ns.comment or "")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="dev-loop")
    p.add_argument("--config", help="config.yaml path (or DEVLOOP_CONFIG)")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("keys", help="SessionStart: print Jira keys")
    s.set_defaults(func=cmd_keys)

    s = sub.add_parser("start", help="Fetch issue, memory, launch spec grill")
    s.add_argument("key")
    s.add_argument("--repo")
    s.set_defaults(func=cmd_start)

    s = sub.add_parser("continue", help="After spec approved: test-writer through PR")
    s.add_argument("key")
    s.add_argument("--repo")
    s.add_argument("--no-wait", action="store_true")
    s.set_defaults(func=cmd_continue)

    s = sub.add_parser("fetch")
    s.add_argument("key")
    s.set_defaults(func=cmd_fetch)

    s = sub.add_parser("memory")
    s.add_argument("--repo")
    s.add_argument("--force", action="store_true")
    s.set_defaults(func=cmd_memory)

    s = sub.add_parser("verify")
    s.add_argument("--repo")
    s.add_argument("--key")
    s.set_defaults(func=cmd_verify)

    s = sub.add_parser("infer")
    s.add_argument("--repo")
    s.set_defaults(func=cmd_infer)

    s = sub.add_parser("status")
    s.set_defaults(func=cmd_status)

    s = sub.add_parser("progress", help="Named stage timeline for a ticket (progress.md)")
    s.add_argument("key", nargs="?")
    s.set_defaults(func=cmd_progress)

    s = sub.add_parser("example-config")
    s.set_defaults(func=cmd_print_example)

    s = sub.add_parser("eval", help="Run configured keys through builtin adapters (test mode)")
    s.add_argument("--repo")
    s.set_defaults(func=cmd_eval)

    s = sub.add_parser("poll", help="Poll watched PRs (launchd). Not a skill, not MCP.")
    s.set_defaults(func=cmd_poll)

    s = sub.add_parser("install-poller", help="Write LaunchAgent plist; load only if poller.enabled")
    s.add_argument("--load", action="store_true", default=None)
    s.add_argument("--no-load", action="store_false", dest="load")
    s.set_defaults(func=cmd_install_poller)

    s = sub.add_parser("repos", help="List ~/dev folder/git candidates for the repo picker")
    s.set_defaults(func=cmd_repos)

    s = sub.add_parser("init-repo", help="Create a new git repo under ~/dev (optional gh create)")
    s.add_argument("name")
    s.set_defaults(func=cmd_init_repo)

    s = sub.add_parser("jira-progress", help="Transition/comment a Jira issue by workflow event name")
    s.add_argument("key")
    s.add_argument("--event", default="on_start", choices=["on_start", "on_pr", "on_merge", "on_block", "on_waiting"])
    s.add_argument("--comment", default="")
    s.set_defaults(func=cmd_jira_progress)
    return p


def main(argv: list[str] | None = None) -> int:
    ns = build_parser().parse_args(argv)
    return int(ns.func(ns) or 0)


if __name__ == "__main__":
    raise SystemExit(main())
