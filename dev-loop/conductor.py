#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import subprocess
import time
from pathlib import Path

from config import DevLoopConfig, jira_creds, load_config
from gitutil import current_branch, default_branch, denylisted, github_remote, is_git_repo, repo_slug, run_git, under_dev
from jira_client import get_issue
from memory import load_or_build
from paths import run_dir
from prompts import review_prompt, simplify_prompt, spec_prompt, test_writer_prompt, writer_prompt
from evidence import capture_evidence
from jira_workflow import progress
from ship import ensure_feature_branch, pr_body, ship_work
from state import load_state, update_state
from touched import changed_since, load_snapshot, save_snapshot, snapshot_tree
from verify_infer import run_verify
from watch import add_watch
from progress import backfill, record

ISSUE_KEY = re.compile(r"^[A-Z][A-Z0-9]+-\d+$")


def require_key(key: str) -> str:
    k = key.strip().upper()
    if not ISSUE_KEY.match(k):
        raise SystemExit(f"dev-loop: bad ticket key {key!r}")
    return k


def require_repo(path: Path, cfg: DevLoopConfig) -> Path:
    repo = path.resolve()
    if not is_git_repo(repo):
        raise SystemExit(f"dev-loop: {repo} is not a git repo")
    slug = repo_slug(repo)
    if cfg.allowlist and slug not in cfg.allowlist:
        raise SystemExit(f"dev-loop: {slug} not in repo.allowlist {cfg.allowlist}")
    if denylisted(repo, cfg.denylist):
        raise SystemExit(f"dev-loop: {slug} is denylisted")
    if cfg.git.require_github_remote and github_remote(repo) is None:
        raise SystemExit(f"dev-loop: {repo} has no GitHub remote (git.require_github_remote)")
    if not under_dev(repo, cfg.dev_root) and not cfg.git.allow_outside_dev and os.environ.get("DEVLOOP_ALLOW_OUTSIDE") != "1":
        raise SystemExit(f"dev-loop: {repo} is not under {cfg.dev_root}")
    return repo


def issue_markdown(issue: dict) -> str:
    comments = "\n".join(f"- {c}" for c in issue.get("comments") or [])
    return (
        f"**{issue.get('key')}** {issue.get('summary')}\n\n"
        f"Type: {issue.get('issuetype')}  Status: {issue.get('status')}\n\n"
        f"{issue.get('description') or ''}\n\n"
        f"## Comments\n{comments or '_none_'}\n"
    )


def fetch_issue(key: str, cfg: DevLoopConfig | None = None) -> Path:
    cfg = cfg or load_config()
    base, email, token = jira_creds(cfg)
    issue = get_issue(
        base,
        email,
        token,
        key,
        issue_path=cfg.jira.issue_path,
        fields=cfg.jira.fields,
        timeout=cfg.jira.timeout_sec,
        comment_limit=cfg.jira.comment_limit,
    )
    dest = run_dir(key)
    (dest / "issue.json").write_text(json.dumps(issue, indent=2) + "\n", encoding="utf-8")
    (dest / "issue.md").write_text(issue_markdown(issue), encoding="utf-8")
    return dest


def launch_prompt(prompt: str, repo: Path, run: Path, name: str, cfg: DevLoopConfig) -> Path:
    dest = run / f"prompt-{name}.md"
    dest.write_text(prompt, encoding="utf-8")
    if cfg.runtime.no_launch or cfg.runtime.agent == "none" or os.environ.get("DEVLOOP_NO_LAUNCH") == "1":
        print(f"dev-loop: wrote {dest} (no_launch)")
        return dest
    script = Path(os.path.expanduser(cfg.runtime.launch_script))
    if cfg.runtime.agent == "cursor":
        print(f"dev-loop: cursor agent — prompt at {dest}")
        return dest
    if not script.is_file():
        print(f"dev-loop: launch script missing ({script}). Prompt written to {dest}")
        return dest
    subprocess.Popen(
        ["bash", str(script), "--file", str(dest), "--cwd", str(repo)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    print(f"dev-loop: launched {name} → {dest}")
    return dest


def wait_file(path: Path, cfg: DevLoopConfig) -> bool:
    if cfg.runtime.builtin_adapters or cfg.runtime.agent == "none":
        return path.is_file()
    start = time.time()
    timeout = max(1, int(cfg.runtime.wait_timeout_sec))
    interval = max(0.05, float(cfg.runtime.poll_interval_sec))
    while time.time() - start < timeout:
        if path.is_file():
            return True
        time.sleep(interval)
    return False


def wait_session_done(run: Path, cfg: DevLoopConfig) -> bool:
    if cfg.runtime.builtin_adapters or cfg.runtime.agent == "none":
        return (run / "STAGE_DONE").is_file() or (run / "SESSION_DONE").is_file()
    start = time.time()
    timeout = max(1, int(cfg.runtime.wait_timeout_sec))
    interval = max(0.05, float(cfg.runtime.poll_interval_sec))
    while time.time() - start < timeout:
        if (run / "STAGE_DONE").is_file() or (run / "SESSION_DONE").is_file():
            return True
        time.sleep(interval)
    return False


def spec_is_approved(run: Path) -> bool:
    return (run / "APPROVED").is_file() or (run / "SPEC_APPROVED").is_file()


def _clear_stage_done(run: Path) -> None:
    for name in ("STAGE_DONE", "SESSION_DONE"):
        p = run / name
        if p.is_file():
            p.unlink()


def _mark_done(run: Path) -> None:
    (run / "STAGE_DONE").write_text("", encoding="utf-8")
    (run / "SESSION_DONE").write_text("", encoding="utf-8")


def _maybe_adapter(stage: str, key: str, repo: Path, run: Path, cfg: DevLoopConfig, **kwargs: object) -> None:
    if not cfg.runtime.builtin_adapters:
        return
    from adapters import run_stage

    run_stage(stage, key=key, repo=repo, run=run, cfg=cfg, **kwargs)
    _mark_done(run)


def start(key: str, repo: Path, cfg: DevLoopConfig | None = None) -> None:
    cfg = cfg or load_config()
    repo = require_repo(repo, cfg)
    key = require_key(key)
    run = fetch_issue(key, cfg)
    load_or_build(repo)
    issue = json.loads((run / "issue.json").read_text(encoding="utf-8"))
    update_state(ticket=key, repo=str(repo), stage="spec", slug=repo_slug(repo), pr_number=None)
    record(run, "fetch", "ok", ticket=key, note=str(repo))
    record(run, "spec", "started", ticket=key)
    progress(cfg, key, "on_start", f"dev-loop started in {repo.name}")
    _clear_stage_done(run)
    for name in ("APPROVED",):
        p = run / name
        if p.is_file():
            p.unlink()
    if cfg.stages_enabled.get("spec", True):
        prompt = spec_prompt(key, run, repo, issue_markdown(issue))
        launch_prompt(prompt, repo, run, "spec", cfg)
        _maybe_adapter("spec", key, repo, run, cfg, issue=issue)
    if cfg.spec_auto_approve:
        if not (run / "spec.md").is_file():
            (run / "spec.md").write_text(issue_markdown(issue), encoding="utf-8")
        (run / "APPROVED").write_text("", encoding="utf-8")
        (run / "SPEC_APPROVED").write_text("spec auto-approved\n", encoding="utf-8")
        record(run, "spec", "auto_approved", ticket=key, note="autonomy.spec_approval=auto")
        print(f"dev-loop: auto-approved spec for {key}")
    else:
        record(run, "spec", "waiting_approval", ticket=key, artifact="spec.md", note="human gate — spec, not the whole ticket")
        print(f"dev-loop: spec waiting approval. Read `{run / 'progress.md'}`.")
        print(f"Accept: touch `{run / 'SPEC_APPROVED'}` (or APPROVED), then continue {key}")
    if cfg.runtime.auto_continue and spec_is_approved(run):
        continue_loop(key, repo, cfg, wait=not cfg.runtime.no_launch)


def continue_loop(key: str, repo: Path | None = None, cfg: DevLoopConfig | None = None, wait: bool = True) -> int:
    cfg = cfg or load_config()
    key = require_key(key)
    st = load_state()
    repo = Path(repo or st.get("repo") or os.getcwd())
    repo = require_repo(repo, cfg)
    run = run_dir(key)
    backfill(run)
    if not spec_is_approved(run):
        raise SystemExit(f"dev-loop: spec not approved — see {run / 'progress.md'}")
    if not (run / "SPEC_APPROVED").is_file() and (run / "APPROVED").is_file():
        (run / "SPEC_APPROVED").write_text("spec approved\n", encoding="utf-8")
        record(run, "spec", "approved", ticket=key, note="human")
    spec = (run / "spec.md").read_text(encoding="utf-8") if (run / "spec.md").is_file() else ""
    issue = json.loads((run / "issue.json").read_text(encoding="utf-8")) if (run / "issue.json").is_file() else {"summary": key}
    summary = str(issue.get("summary") or key)
    mem = load_or_build(repo)
    contracts = (mem / "contracts.md").read_text(encoding="utf-8") if (mem / "contracts.md").is_file() else ""

    ensure_feature_branch(
        repo,
        key,
        summary,
        never_commit=cfg.git.never_commit_branches,
        pattern=cfg.git.branch_pattern,
        slug_max_len=cfg.git.slug_max_len,
    )
    snap_path = run / "baseline.json"
    save_snapshot(snap_path, snapshot_tree(repo))

    if cfg.stages_enabled.get("test_writer", True):
        update_state(stage="test-writer", ticket=key, repo=str(repo))
        record(run, "test_writer", "started", ticket=key)
        _clear_stage_done(run)
        launch_prompt(test_writer_prompt(key, run, repo, spec, contracts), repo, run, "test-writer", cfg)
        _maybe_adapter("test_writer", key, repo, run, cfg, spec=spec)
        if wait and not cfg.runtime.builtin_adapters and not wait_session_done(run, cfg):
            record(run, "test_writer", "timeout", ticket=key)
            raise SystemExit("dev-loop: test-writer timed out")
        record(run, "test_writer", "ok", ticket=key)

    verify_log = ""
    writer_n = max(1, cfg.caps.writer_retries)
    if cfg.stages_enabled.get("writer", True) or cfg.stages_enabled.get("verify", True):
        for attempt in range(1, writer_n + 1):
            if cfg.stages_enabled.get("writer", True):
                update_state(stage="writer", ticket=key, attempt=attempt)
                record(run, "writer", "started", ticket=key, note=f"attempt {attempt}")
                _clear_stage_done(run)
                launch_prompt(writer_prompt(key, run, repo, spec, verify_log), repo, run, f"writer-{attempt}", cfg)
                _maybe_adapter("writer", key, repo, run, cfg, spec=spec, attempt=attempt)
                if wait and not cfg.runtime.builtin_adapters and not wait_session_done(run, cfg):
                    raise SystemExit("dev-loop: writer timed out")
            if not cfg.stages_enabled.get("verify", True):
                break
            rc = run_verify(repo, cfg, run / "verify.log")
            verify_log = (run / "verify.log").read_text(encoding="utf-8") if (run / "verify.log").is_file() else ""
            if rc == 0:
                record(run, "verify", "ok", ticket=key, note=f"attempt {attempt}")
                break
            record(run, "verify", "failed", ticket=key, note=f"attempt {attempt} exit {rc}")
            if attempt == writer_n:
                print(f"dev-loop: verify still red after {writer_n} writer attempts; not opening a PR")
                update_state(stage="failed-verify")
                record(run, "verify", "exhausted", ticket=key)
                progress(cfg, key, "on_block", "verify still red after writer retries")
                return rc

    if cfg.stages_enabled.get("simplify", False):
        update_state(stage="simplify", ticket=key)
        record(run, "simplify", "started", ticket=key)
        _clear_stage_done(run)
        launch_prompt(simplify_prompt(key, run, repo, spec), repo, run, "simplify", cfg)
        _maybe_adapter("simplify", key, repo, run, cfg)
        if wait and not cfg.runtime.builtin_adapters and not wait_session_done(run, cfg):
            record(run, "simplify", "timeout", ticket=key)
            raise SystemExit("dev-loop: simplify timed out")
        if cfg.stages_enabled.get("verify", True):
            rc = run_verify(repo, cfg, run / "verify.log")
            if rc != 0:
                record(run, "verify", "failed", ticket=key, note="after simplify")
                print("dev-loop: verify red after simplify; not opening a PR")
                update_state(stage="failed-verify")
                progress(cfg, key, "on_block", "verify red after simplify")
                return rc
        record(run, "simplify", "ok", ticket=key)

    evidence_md = ""
    if cfg.evidence.enabled:
        evidence_md = capture_evidence(cfg, repo, run / "evidence.md")

    verdict: dict = {"verdict": cfg.review.default_verdict, "summary": "", "risks": []}
    if cfg.stages_enabled.get("review", True):
        review_n = max(1, cfg.caps.review_retries)
        for attempt in range(1, review_n + 1):
            update_state(stage="review", attempt=attempt)
            record(run, "review", "started", ticket=key, note=f"attempt {attempt}")
            _clear_stage_done(run)
            launch_prompt(review_prompt(key, run, repo, spec), repo, run, f"review-{attempt}", cfg)
            _maybe_adapter("review", key, repo, run, cfg)
            if wait and not cfg.runtime.builtin_adapters and not wait_session_done(run, cfg):
                raise SystemExit("dev-loop: review timed out")
            if (run / "verdict.json").is_file():
                try:
                    verdict = json.loads((run / "verdict.json").read_text(encoding="utf-8"))
                except json.JSONDecodeError:
                    verdict = {"verdict": "needs_improvement", "summary": "unreadable verdict.json"}
            v = str(verdict.get("verdict") or "").lower().replace(" ", "-")
            verdict["verdict"] = v
            if v in set(cfg.review.pass_verdicts):
                record(run, "review", "pass", ticket=key, note=v)
                if cfg.stages_enabled.get("verify", True):
                    rc = run_verify(repo, cfg, run / "verify.log")
                    if rc != 0:
                        record(run, "verify", "failed_after_review", ticket=key, note=f"attempt {attempt}")
                        if attempt < review_n and cfg.stages_enabled.get("writer", True):
                            verify_log = (run / "verify.log").read_text(encoding="utf-8") if (run / "verify.log").is_file() else ""
                            launch_prompt(
                                writer_prompt(key, run, repo, spec, f"verify failed after review\n{verify_log}"),
                                repo,
                                run,
                                f"rewrite-verify-{attempt}",
                                cfg,
                            )
                            _maybe_adapter("writer", key, repo, run, cfg, spec=spec, attempt=attempt)
                            continue
                        print("dev-loop: verify red after review; not opening a PR")
                        update_state(stage="failed-verify")
                        progress(cfg, key, "on_block", "verify red after review")
                        return rc
                break
            record(run, "review", "rewrite", ticket=key, note=v)
            if v in set(cfg.review.rewrite_verdicts) and attempt < review_n and cfg.stages_enabled.get("writer", True):
                update_state(stage="writer")
                _clear_stage_done(run)
                launch_prompt(writer_prompt(key, run, repo, spec, f"review: {v}\n{verdict}"), repo, run, f"rewrite-{attempt}", cfg)
                _maybe_adapter("writer", key, repo, run, cfg, spec=spec, attempt=attempt)
                continue
            break

    if not cfg.stages_enabled.get("ship", True):
        update_state(stage="skipped-ship", ticket=key)
        return 0

    rels = changed_since(repo, load_snapshot(snap_path))
    (run / "touched.txt").write_text("\n".join(rels) + ("\n" if rels else ""), encoding="utf-8")
    body = pr_body(key, summary, spec, verdict, True, evidence=evidence_md)
    (run / "pr.md").write_text(body, encoding="utf-8")
    try:
        prs = ship_work(repo, rels, key, summary, spec, verdict, cfg, evidence=evidence_md)
    except Exception as exc:  # noqa: BLE001
        branch = current_branch(repo)
        update_state(stage="ship-failed", error=str(exc), branch=branch)
        print(f"dev-loop: commit local; push/PR failed: {exc}")
        return 1
    branch = current_branch(repo)
    if cfg.git.merge_to_default_after_ship:
        base = default_branch(repo)
        run_git(repo, "checkout", base)
        run_git(repo, "merge", "--no-edit", branch)
    if not cfg.git.push:
        update_state(stage="shipped-local", pr_number=None, branch=branch, pr_numbers=[])
        record(run, "ship", "local", ticket=key, note=branch)
        print(f"dev-loop: local commit on {branch} (git.push false)")
        return 0
    for prn in prs:
        add_watch({"pr": prn, "repo": str(repo), "key": key, "branch": branch})
    last = prs[-1] if prs else None
    update_state(stage="shipped", pr_number=last, pr_numbers=prs, branch=branch)
    if last:
        progress(cfg, key, "on_pr", f"PR #{last} opened on {branch}")
        record(run, "ship", "pr", ticket=key, note=f"#{last} {branch}")
        print(f"dev-loop: PR #{last} on {branch}" + (f" (stack {len(prs)})" if len(prs) > 1 else ""))
    else:
        record(run, "ship", "pushed", ticket=key, note=branch)
        print(f"dev-loop: pushed {branch} (no PR number parsed)")
    return 0
