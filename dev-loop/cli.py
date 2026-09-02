#!/usr/bin/env python3
"""dev-loop CLI. After install: python3 ~/.claude/hooks/dev-loop/cli.py"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from brief import Document, emit, fail  # noqa: E402
from brief.ports import (  # noqa: E402
    HomePort,
    InferPort,
    KeysPort,
    PollPort,
    ProgressPort,
    ReposPort,
    StatusPort,
    TicketPort,
)
from config import example_yaml, load_config  # noqa: E402
from conductor import continue_loop, fetch_issue, require_key, require_repo, start  # noqa: E402
from memory import index_is_fresh, load_or_build  # noqa: E402
from paths import run_dir  # noqa: E402
from state import load_state  # noqa: E402
from verify_infer import infer_recipe, run_verify  # noqa: E402


def _cfg(ns: argparse.Namespace):
    path = getattr(ns, "config", None)
    return load_config(Path(path).expanduser() if path else None)


def _fmt(ns: argparse.Namespace) -> str:
    return str(getattr(ns, "format", None) or "brief")


def _full(ns: argparse.Namespace) -> bool:
    return bool(getattr(ns, "full", False))


def _show(text: str) -> int:
    sys.stdout.write(text if text.endswith("\n") else text + "\n")
    return 0


def cmd_home(ns: argparse.Namespace) -> int:
    return _show(HomePort().view(fmt=_fmt(ns), full=_full(ns)))


def cmd_keys(ns: argparse.Namespace) -> int:
    try:
        return _show(
            KeysPort().view(
                cfg=_cfg(ns),
                fmt=_fmt(ns),
                full=_full(ns),
                recent=bool(getattr(ns, "recent", False)),
                silent=False,
            )
        )
    except Exception as exc:
        return fail(str(exc))


def cmd_start(ns: argparse.Namespace) -> int:
    from budget import BudgetExhausted
    from pick import resolve_repo

    cfg = _cfg(ns)
    repo = resolve_repo(cfg, ns.repo, require=None)
    try:
        start(ns.key, repo, cfg)
    except BudgetExhausted as exc:
        return fail(str(exc), code=2)
    return 0


def cmd_continue(ns: argparse.Namespace) -> int:
    from budget import BudgetExhausted
    from pick import resolve_repo
    from step import step

    cfg = _cfg(ns)
    if ns.repo:
        repo = resolve_repo(cfg, ns.repo, require=None)
    else:
        st = load_state()
        repo = Path(st["repo"]).expanduser() if st.get("repo") else resolve_repo(cfg, None, require=None)
    if cfg.runtime.agent == "cursor":
        try:
            return step(ns.key, repo, cfg)
        except BudgetExhausted as exc:
            return fail(str(exc), code=2)
    wait = not ns.no_wait
    try:
        return continue_loop(ns.key, repo, cfg, wait=wait)
    except BudgetExhausted as exc:
        return fail(str(exc), code=2)


def cmd_step(ns: argparse.Namespace) -> int:
    from budget import BudgetExhausted
    from pick import resolve_repo
    from step import step

    cfg = _cfg(ns)
    if ns.repo:
        repo = resolve_repo(cfg, ns.repo, require=None)
    else:
        st = load_state()
        repo = Path(st["repo"]).expanduser() if st.get("repo") else resolve_repo(cfg, None, require=None)
    try:
        return step(ns.key, repo, cfg)
    except BudgetExhausted as exc:
        return fail(str(exc), code=2)


def cmd_approve(ns: argparse.Namespace) -> int:
    from conductor import approve_spec, require_key
    from paths import run_dir

    key = require_key(ns.key)
    run = run_dir(key)
    try:
        approve_spec(run, key)
    except FileNotFoundError as exc:
        return fail(str(exc), code=2)
    print(f"dev-loop: spec approved for {key}")
    return cmd_step(ns)


def cmd_arch_approve(ns: argparse.Namespace) -> int:
    from arch_studio_bridge import approve_arch
    from conductor import require_key
    from paths import run_dir

    key = require_key(ns.key)
    run = run_dir(key)
    try:
        approve_arch(run, key)
    except FileNotFoundError as exc:
        return fail(str(exc), code=2)
    print(f"dev-loop: architecture approved for {key}")
    return 0


def cmd_arch_reject(ns: argparse.Namespace) -> int:
    from arch_studio_bridge import reject_arch
    from conductor import require_key
    from paths import run_dir

    key = require_key(ns.key)
    run = run_dir(key)
    reject_arch(run, key, note=str(getattr(ns, "note", "") or ""))
    print(f"dev-loop: architecture rejected for {key}")
    return 0


def cmd_arch_status(ns: argparse.Namespace) -> int:
    from arch_studio_bridge import arch_status
    from conductor import require_key
    from paths import run_dir

    key = require_key(ns.key)
    payload = arch_status(run_dir(key))
    if _fmt(ns) == "json":
        print(json.dumps(payload, indent=2))
        return 0
    lines = [
        f"enabled: {payload['enabled']}",
        f"require_review: {payload['require_review']}",
        f"approved: {payload['approved']}",
        f"reason: {payload['reason'] or '-'}",
    ]
    if payload.get("review_html"):
        lines.append(f"review_html: {payload['review_html']}")
    if payload.get("output_dir"):
        lines.append(f"output_dir: {payload['output_dir']}")
    return _show("\n".join(lines) + "\n")


def cmd_repos(ns: argparse.Namespace) -> int:
    from pick import candidates_payload

    payload = candidates_payload(_cfg(ns))
    if _fmt(ns) == "json":
        print(json.dumps(payload, indent=2))
        return 0
    return _show(ReposPort().view(payload=payload, fmt="brief", full=_full(ns)))


def cmd_init_repo(ns: argparse.Namespace) -> int:
    from pick import init_repo

    dest = init_repo(_cfg(ns), ns.name)
    return _show(
        emit(
            Document(
                bin="cli.py",
                description="created repo",
                meta={"path": str(dest)},
                help=["Run `cli.py start <key> --repo " + str(dest) + "`"],
            ),
            fmt=_fmt(ns),
            full=_full(ns),
        )
    )


def cmd_fetch(ns: argparse.Namespace) -> int:
    dest = fetch_issue(require_key(ns.key), _cfg(ns))
    issue_path = dest / "issue.json"
    issue = {}
    if issue_path.is_file():
        try:
            issue = json.loads(issue_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            issue = {}
    return _show(TicketPort().view(issue=issue, path=str(issue_path), fmt=_fmt(ns), full=_full(ns)))


def cmd_memory(ns: argparse.Namespace) -> int:
    cfg = _cfg(ns)
    repo = Path(ns.repo).expanduser().resolve() if ns.repo else Path.cwd()
    repo = require_repo(repo, cfg)
    if ns.force:
        from memory import regenerate

        mem = regenerate(repo)
        fresh = "regenerated"
    else:
        mem = load_or_build(repo)
        fresh = "fresh" if index_is_fresh(repo) else "rebuilt"
    return _show(
        emit(
            Document(
                bin="cli.py",
                description="repo memory",
                meta={"path": str(mem), "state": fresh},
                help=["Run `cli.py start <key> --repo " + str(repo) + "`"],
            ),
            fmt=_fmt(ns),
        )
    )




def cmd_agent_memory(ns: argparse.Namespace) -> int:
    """Apply durable metadata from a verdict.json into the target repo."""
    from agent_memory import ApplyError, apply_verdict_file
    from paths import run_dir

    repo = Path(ns.repo).expanduser().resolve() if ns.repo else Path.cwd()
    if ns.verdict:
        verdict_path = Path(ns.verdict).expanduser().resolve()
    elif ns.key:
        verdict_path = run_dir(str(ns.key)) / "verdict.json"
    else:
        return fail("pass --verdict PATH or --key TICKET", code=2)
    if not verdict_path.is_file():
        return fail(f"no verdict at {verdict_path}", code=2)
    try:
        results = apply_verdict_file(repo, verdict_path)
    except ApplyError as exc:
        return fail(str(exc), code=2)
    except json.JSONDecodeError as exc:
        return fail(f"verdict unreadable: {exc}", code=2)
    applied = sum(1 for r in results if r.get("status") == "applied")
    rejected = sum(1 for r in results if r.get("status") == "rejected")
    return _show(
        emit(
            Document(
                bin="cli.py",
                description="agent-memory apply",
                meta={
                    "repo": str(repo),
                    "verdict": str(verdict_path),
                    "applied": applied,
                    "rejected": rejected,
                    "results": results,
                },
                help=["Write durable metadata[] on verdict.json; harness applies AGENTS.md / path-scoped rules."],
            ),
            fmt=_fmt(ns),
            full=_full(ns),
        )
    )


def cmd_verify(ns: argparse.Namespace) -> int:
    from treehouse import workspace_for_ticket

    cfg = _cfg(ns)
    st = load_state()
    key = ns.key or st.get("ticket") or "LOCAL"
    repo_arg = Path(ns.repo).expanduser() if ns.repo else None
    run = run_dir(str(key))
    leased = (run / "lease.json").is_file()
    repo = workspace_for_ticket(str(key), repo_arg, st)
    repo = require_repo(repo, cfg, check_location=not leased)
    return run_verify(repo, cfg, run / "verify.log")


def cmd_status(ns: argparse.Namespace) -> int:
    return _show(StatusPort().view(fmt=_fmt(ns), full=_full(ns)))


def cmd_progress(ns: argparse.Namespace) -> int:
    key = ns.key or load_state().get("ticket")
    if not key:
        return fail("no ticket — pass KEY or start a loop first", code=2)
    run = run_dir(str(key))
    if not run.is_dir():
        return fail(f"no run dir {run}", code=2)
    if _full(ns):
        from progress import backfill

        backfill(run)
        print((run / "progress.md").read_text(encoding="utf-8"))
        return 0
    return _show(ProgressPort().view(key=str(key), run=run, fmt=_fmt(ns), full=False))


def cmd_infer(ns: argparse.Namespace) -> int:
    from treehouse import workspace_for_ticket

    cfg = _cfg(ns)
    st = load_state()
    key = getattr(ns, "key", None) or st.get("ticket")
    repo_arg = Path(ns.repo).expanduser() if ns.repo else None
    if key:
        repo = workspace_for_ticket(str(key), repo_arg, st)
    else:
        repo = (repo_arg or Path.cwd()).expanduser().resolve()
    r = infer_recipe(repo, cfg)
    if r is None:
        return fail("cannot infer", code=2)
    return _show(InferPort().view(recipe=r, fmt=_fmt(ns), full=_full(ns)))


def cmd_print_example(_: argparse.Namespace) -> int:
    print(example_yaml())
    return 0


def cmd_eval(ns: argparse.Namespace) -> int:
    from eval_harness import run_eval

    return run_eval(_cfg(ns), Path(ns.repo).expanduser() if ns.repo else None)


def cmd_poll(ns: argparse.Namespace) -> int:
    from poller import poll_once

    actions = poll_once(_cfg(ns))
    return _show(PollPort().view(actions=list(actions), fmt=_fmt(ns), full=_full(ns)))


def cmd_install_poller(ns: argparse.Namespace) -> int:
    from poller import install_poller

    dest = install_poller(_cfg(ns), load=None if ns.load is None else bool(ns.load))
    return _show(
        emit(
            Document(bin="cli.py", description="poller plist", meta={"path": str(dest)}),
            fmt=_fmt(ns),
        )
    )


def cmd_jira_progress(ns: argparse.Namespace) -> int:
    from jira_workflow import progress

    cfg = _cfg(ns)
    key = require_key(ns.key)
    result = progress(cfg, key, ns.event, ns.comment or "")
    return _show(
        emit(
            Document(
                bin="cli.py",
                description="jira workflow",
                meta={
                    "key": key,
                    "event": ns.event,
                    "status": result.get("status") or "ok",
                    "note": result.get("note") or "",
                },
            ),
            fmt=_fmt(ns),
        )
    )


def build_parser() -> argparse.ArgumentParser:
    g = argparse.ArgumentParser(add_help=False)
    g.add_argument("--config", help="config.yaml path (or DEVLOOP_CONFIG)")
    g.add_argument("--format", choices=["brief", "json"], default="brief", help="agent output (default brief)")
    g.add_argument("--full", action="store_true", help="do not clip long fields")
    # Same flags after the subcommand. SUPPRESS so subparser defaults do not
    # overwrite values already set on the parent (`dev-loop --format json repos`).
    after = argparse.ArgumentParser(add_help=False)
    after.add_argument("--config")
    after.add_argument("--format", choices=["brief", "json"], default=argparse.SUPPRESS)
    after.add_argument("--full", action="store_true", default=argparse.SUPPRESS)
    p = argparse.ArgumentParser(prog="dev-loop", parents=[g])
    sub = p.add_subparsers(dest="cmd", required=False)

    def add(name: str, **kw: object) -> argparse.ArgumentParser:
        return sub.add_parser(name, parents=[after], **kw)

    s = add("keys", help="Open Jira keys (brief)")
    s.add_argument("--recent", action="store_true", help="Ignore sprint JQL; last-updated in jira.project")
    s.set_defaults(func=cmd_keys)

    s = add("start", help="Fetch issue, memory, launch spec grill")
    s.add_argument("key")
    s.add_argument("--repo")
    s.set_defaults(func=cmd_start)

    s = add("continue", help="After spec approved: test-writer through PR (blocking unless agent=cursor)")
    s.add_argument("key")
    s.add_argument("--repo")
    s.add_argument("--no-wait", action="store_true")
    s.set_defaults(func=cmd_continue)

    s = add("step", help="Cursor: run the next incomplete stage and return (never polls)")
    s.add_argument("key")
    s.add_argument("--repo")
    s.set_defaults(func=cmd_step)

    s = add("approve", help="Record spec approval (SPEC_APPROVED) and step once")
    s.add_argument("key")
    s.add_argument("--repo")
    s.set_defaults(func=cmd_approve)

    arch = sub.add_parser("arch", help="Architecture pack review gate (Arch Studio)", parents=[after])
    arch_sub = arch.add_subparsers(dest="arch_cmd", required=True)
    s = arch_sub.add_parser("approve", help="Record ARCH_APPROVED after in-chat review")
    s.add_argument("key")
    s.set_defaults(func=cmd_arch_approve)
    s = arch_sub.add_parser("reject", help="Clear ARCH_APPROVED and record rejection")
    s.add_argument("key")
    s.add_argument("--note", default="", help="Reviewer note for review-decisions.json")
    s.set_defaults(func=cmd_arch_reject)
    s = arch_sub.add_parser("status", help="Show architecture review paths and gate state")
    s.add_argument("key")
    s.set_defaults(func=cmd_arch_status)

    s = add("fetch")
    s.add_argument("key")
    s.set_defaults(func=cmd_fetch)

    s = add("memory")
    s.add_argument("--repo")
    s.add_argument("--force", action="store_true")
    s.set_defaults(func=cmd_memory)

    s = add("agent-memory", help="Apply verdict.metadata[] into AGENTS.md / path-scoped rules")
    s.add_argument("--repo", help="Target git repo (default: cwd)")
    s.add_argument("--verdict", help="Path to verdict.json")
    s.add_argument("--key", help="Ticket key; reads runs/KEY/verdict.json")
    s.set_defaults(func=cmd_agent_memory)

    s = add("verify")
    s.add_argument("--repo")
    s.add_argument("--key")
    s.set_defaults(func=cmd_verify)

    s = add("infer")
    s.add_argument("--repo")
    s.set_defaults(func=cmd_infer)

    s = add("status")
    s.set_defaults(func=cmd_status)

    s = add("progress", help="Stage timeline (brief; --full for progress.md)")
    s.add_argument("key", nargs="?")
    s.set_defaults(func=cmd_progress)

    s = add("example-config")
    s.set_defaults(func=cmd_print_example)

    s = add("eval", help="Run configured keys through builtin adapters (test mode)")
    s.add_argument("--repo")
    s.set_defaults(func=cmd_eval)

    s = add("poll", help="Poll watched PRs (launchd). Not a skill, not MCP.")
    s.set_defaults(func=cmd_poll)

    s = add("install-poller", help="Write LaunchAgent plist; load only if poller.enabled")
    s.add_argument("--load", action="store_true", default=None)
    s.add_argument("--no-load", action="store_false", dest="load")
    s.set_defaults(func=cmd_install_poller)

    s = add("repos", help="Candidate repos (brief; --format json for the picker)")
    s.set_defaults(func=cmd_repos)

    s = add("init-repo", help="Create a new git repo under ~/dev (optional gh create)")
    s.add_argument("name")
    s.set_defaults(func=cmd_init_repo)

    s = add("jira-progress", help="Transition/comment a Jira issue by workflow event name")
    s.add_argument("key")
    s.add_argument("--event", default="on_start", choices=["on_start", "on_pr", "on_merge", "on_block", "on_waiting"])
    s.add_argument("--comment", default="")
    s.set_defaults(func=cmd_jira_progress)
    return p


def main(argv: list[str] | None = None) -> int:
    ns = build_parser().parse_args(argv)
    func = getattr(ns, "func", None) or cmd_home
    return int(func(ns) or 0)


if __name__ == "__main__":
    raise SystemExit(main())
