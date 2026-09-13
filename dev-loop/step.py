#!/usr/bin/env python3
"""One-stage stepper for Cursor. Never polls."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from config import DevLoopConfig
from conductor import spec_is_approved
from progress import load_status, record

LAUNCH_TO_PROGRESS = {
    "test-writer": "test_writer",
    "writer": "writer",
    "review": "review",
    "simplify": "simplify",
}

WAITABLE = frozenset(LAUNCH_TO_PROGRESS)


def _record_memory(cfg: DevLoopConfig, repo: Path, run: Path, key: str) -> None:
    from agent_memory import apply_run_memory

    results = apply_run_memory(cfg, repo, run)
    if results:
        record(
            run,
            "agent-memory",
            "applied" if any(r.get("status") == "applied" for r in results) else "noop",
            ticket=key,
            note=str(len(results)),
        )


@dataclass(frozen=True)
class StepPlan:
    kind: str
    stage: str


def _history(run: Path) -> list[dict[str, Any]]:
    hist = load_status(run).get("history") or []
    return [ev for ev in hist if isinstance(ev, dict)]


def _ok(run: Path, stage: str, statuses: frozenset[str] | None = None) -> bool:
    good = statuses or frozenset({"ok", "pass", "pr", "local", "approved", "auto_approved"})
    return any(ev.get("stage") == stage and ev.get("status") in good for ev in _history(run))


def _last(run: Path) -> dict[str, Any]:
    hist = _history(run)
    return hist[-1] if hist else {}


def _done_files(run: Path) -> bool:
    return (run / "STAGE_DONE").is_file() or (run / "SESSION_DONE").is_file()


def consume_done(run: Path, launched_stage: str | None) -> str | None:
    if not launched_stage or launched_stage not in WAITABLE:
        return None
    if not _done_files(run):
        return None
    progress_stage = LAUNCH_TO_PROGRESS[launched_stage]
    record(run, progress_stage, "ok")
    for name in ("STAGE_DONE", "SESSION_DONE"):
        p = run / name
        if p.is_file():
            p.unlink()
    return progress_stage


def plan_step(run: Path, cfg: DevLoopConfig, launched_stage: str | None) -> StepPlan:
    if not spec_is_approved(run):
        return StepPlan(kind="need_spec", stage="spec")
    if launched_stage in WAITABLE and not _ok(run, LAUNCH_TO_PROGRESS[launched_stage]):
        return StepPlan(kind="wait", stage=LAUNCH_TO_PROGRESS[launched_stage])

    stages = cfg.stages_enabled
    if stages.get("test_writer", True) and not _ok(run, "test_writer"):
        return StepPlan(kind="setup", stage="test_writer")

    if stages.get("verify", True) and not _ok(run, "verify"):
        last = _last(run)
        if last.get("stage") == "writer" and last.get("status") == "ok":
            return StepPlan(kind="verify", stage="verify")
        return StepPlan(kind="setup", stage="writer")

    if stages.get("writer", True) and not stages.get("verify", True) and not _ok(run, "writer"):
        return StepPlan(kind="setup", stage="writer")

    if stages.get("simplify", False) and not _ok(run, "simplify"):
        return StepPlan(kind="setup", stage="simplify")

    if stages.get("review", True) and not _ok(run, "review", frozenset({"ok", "pass"})):
        return StepPlan(kind="setup", stage="review")

    if getattr(cfg.evidence, "enabled", False) and not _ok(run, "evidence"):
        return StepPlan(kind="evidence", stage="evidence")

    if stages.get("ship", True) and not _ok(run, "ship", frozenset({"ok", "pr", "local"})):
        return StepPlan(kind="ship", stage="ship")

    return StepPlan(kind="done", stage="done")


PROGRESS_TO_LAUNCH = {v: k for k, v in LAUNCH_TO_PROGRESS.items()}


def step(key: str, repo: Path | None, cfg: DevLoopConfig) -> int:
    import json

    from conductor import launch_prompt, require_key, require_repo, _clear_stage_done
    from lavish import decide_lavish
    from memory import load_or_build
    from paths import run_dir
    from prompts import review_prompt, simplify_prompt, test_writer_prompt, writer_prompt
    from ship import ensure_feature_branch, pr_body, pr_body_inputs, ship_work
    from state import load_state, update_state
    from touched import changed_since, load_snapshot, save_snapshot, snapshot_tree
    from treehouse import workspace_for_ticket, workspace_notice
    from verify_infer import run_verify
    from evidence import capture_evidence
    from jira_workflow import pr_comment_text, progress as jira_progress
    from watch import add_watch
    from gitutil import current_branch, default_branch, run_git

    key = require_key(key)
    run = run_dir(key)
    st = load_state()
    launched = str(st.get("stage") or "")
    if launched not in WAITABLE:
        launched = None
    consumed = consume_done(run, launched)
    plan = plan_step(run, cfg, None if consumed else launched)
    if plan.kind == "need_spec":
        print(f"dev-loop: spec not approved — see {run / 'progress.md'}")
        return 2

    leased = (run / "lease.json").is_file()
    repo_path = workspace_for_ticket(key, repo, st)
    repo_path = require_repo(repo_path, cfg, check_location=not leased)
    origin = Path(st.get("origin_repo") or st.get("repo") or repo_path)
    print(workspace_notice(repo_path))

    if consumed == "review":
        _record_memory(cfg, repo_path, run, key)

    if plan.kind == "wait":
        print(f"dev-loop: waiting for STAGE_DONE ({plan.stage}) under {run}")
        return 0
    if plan.kind == "done":
        print(f"dev-loop: {key} complete")
        return 0

    issue = {"summary": key}
    if (run / "issue.json").is_file():
        try:
            issue = json.loads((run / "issue.json").read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            issue = {"summary": key}
    summary = str(issue.get("summary") or key)
    spec = (run / "spec.md").read_text(encoding="utf-8") if (run / "spec.md").is_file() else ""
    mem = load_or_build(repo_path)
    contracts = (mem / "contracts.md").read_text(encoding="utf-8") if (mem / "contracts.md").is_file() else ""
    lv = decide_lavish(cfg, repo_path)

    if not (run / "baseline.json").is_file():
        ensure_feature_branch(
            repo_path,
            key,
            summary,
            never_commit=cfg.git.never_commit_branches,
            pattern=cfg.git.branch_pattern,
            slug_max_len=cfg.git.slug_max_len,
        )
        save_snapshot(run / "baseline.json", snapshot_tree(repo_path))

    if plan.kind == "setup":
        _clear_stage_done(run)
        launch = PROGRESS_TO_LAUNCH[plan.stage]
        update_state(stage=launch, ticket=key, repo=str(repo_path), origin_repo=str(origin))
        record(run, plan.stage, "started", ticket=key)
        if plan.stage == "test_writer":
            prompt = test_writer_prompt(key, run, repo_path, spec, contracts)
            dest = launch_prompt(prompt, repo_path, run, "test-writer", cfg)
        elif plan.stage == "writer":
            verify_log = (run / "verify.log").read_text(encoding="utf-8") if (run / "verify.log").is_file() else ""
            prompt = writer_prompt(key, run, repo_path, spec, verify_log, lavish=lv.enabled)
            dest = launch_prompt(prompt, repo_path, run, "writer", cfg)
        elif plan.stage == "simplify":
            prompt = simplify_prompt(key, run, repo_path, spec)
            dest = launch_prompt(prompt, repo_path, run, "simplify", cfg)
        else:
            prompt = review_prompt(key, run, repo_path, spec)
            dest = launch_prompt(prompt, repo_path, run, "review", cfg)
        print(f"dev-loop: step {plan.stage} — do the prompt, write STAGE_DONE, then step again")
        print(f"  prompt: {dest}")
        return 0

    if plan.kind == "verify":
        rc = run_verify(repo_path, cfg, run / "verify.log")
        if rc == 0:
            record(run, "verify", "ok", ticket=key)
            print(f"dev-loop: verify ok for {key}")
            return 0
        record(run, "verify", "failed", ticket=key, note=str(rc))
        print(f"dev-loop: verify failed (exit {rc}); next step retries writer")
        return rc

    if plan.kind == "evidence":
        capture_evidence(cfg, repo_path, run / "evidence.md")
        record(run, "evidence", "ok", ticket=key)
        return 0

    if plan.kind == "ship":
        _record_memory(cfg, repo_path, run, key)
        rels = changed_since(repo_path, load_snapshot(run / "baseline.json"))
        (run / "touched.txt").write_text("\n".join(rels) + ("\n" if rels else ""), encoding="utf-8")
        verdict: dict = {"verdict": cfg.review.default_verdict, "summary": "", "risks": []}
        if (run / "verdict.json").is_file():
            try:
                verdict = json.loads((run / "verdict.json").read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                pass
        evidence_md = (run / "evidence.md").read_text(encoding="utf-8") if (run / "evidence.md").is_file() else ""
        extras = pr_body_inputs(cfg, repo_path, run)
        body = pr_body(key, summary, spec, verdict, True, evidence=evidence_md, **extras)
        (run / "pr.md").write_text(body, encoding="utf-8")
        try:
            prs = ship_work(
                repo_path, rels, key, summary, spec, verdict, cfg, evidence=evidence_md, run=run, **extras
            )
        except Exception as exc:  # noqa: BLE001
            update_state(stage="ship-failed", error=str(exc), ticket=key)
            print(f"dev-loop: ship failed: {exc}")
            return 1
        branch = current_branch(repo_path)
        if cfg.git.merge_to_default_after_ship:
            base = default_branch(repo_path)
            run_git(repo_path, "checkout", base)
            run_git(repo_path, "merge", "--no-edit", branch)
        if not cfg.git.push:
            update_state(stage="shipped-local", pr_number=None, branch=branch, ticket=key)
            record(run, "ship", "local", ticket=key, note=branch)
            print(f"dev-loop: local commit on {branch}")
            return 0
        for prn in prs:
            add_watch({"pr": prn, "repo": str(repo_path), "key": key, "branch": branch})
        last = prs[-1] if prs else None
        update_state(stage="shipped", pr_number=last, pr_numbers=prs, branch=branch, ticket=key)
        if last:
            jira_progress(cfg, key, "on_pr", pr_comment_text(cfg, last, branch, repo=repo_path))
            record(run, "ship", "pr", ticket=key, note=f"#{last} {branch}")
            print(f"dev-loop: PR #{last} on {branch}")
        else:
            record(run, "ship", "pushed", ticket=key, note=branch)
            print(f"dev-loop: pushed {branch}")
        return 0

    print(f"dev-loop: unknown step {plan.kind}")
    return 2
