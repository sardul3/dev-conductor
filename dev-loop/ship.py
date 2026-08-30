#!/usr/bin/env python3
from __future__ import annotations

import re
import subprocess
from pathlib import Path

from conventional import is_conventional, rewrite_subject
from gitutil import current_branch, default_branch, is_unpushed, run_git
from stack import split_paths

KEY_RE = re.compile(r"^[A-Z][A-Z0-9]+-\d+$")


def slugify(text: str, max_len: int = 40) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return (s or "work")[:max_len].strip("-") or "work"


def branch_name(key: str, summary: str, pattern: str = "feat/{key}-{slug}", slug_max_len: int = 40) -> str:
    return pattern.format(key=key, slug=slugify(summary, slug_max_len))


def conventional_message(key: str, summary: str, body: str = "", commit_type: str = "feat") -> str:
    title = (summary or "change").strip().rstrip(".")
    head = f"{commit_type}: {title} ({key})"
    extra = (body or "").strip()
    if extra:
        return head + "\n\n" + extra[:2000] + "\n"
    return head + "\n"


def ensure_feature_branch(
    repo: Path,
    key: str,
    summary: str,
    never_commit: list[str] | None = None,
    pattern: str = "feat/{key}-{slug}",
    slug_max_len: int = 40,
) -> str:
    banned = set(never_commit or ["main", "master"])
    name = branch_name(key, summary, pattern, slug_max_len)
    base = default_branch(repo)
    cur = current_branch(repo)
    if cur in banned or cur != name:
        run_git(repo, "checkout", "-B", name, base)
    return name


def stage_paths(repo: Path, rels: list[str]) -> None:
    if not rels:
        return
    run_git(repo, "add", "--", *rels)


def commit_if_needed(repo: Path, message: str) -> bool:
    staged = run_git(repo, "diff", "--cached", "--name-only")
    if not staged:
        return False
    run_git(repo, "commit", "-m", message)
    return True


def maybe_rewrite_head(repo: Path, key: str, commit_type: str, enabled: bool) -> None:
    if not enabled:
        return
    subj = run_git(repo, "log", "-1", "--format=%s", check=False)
    if not subj or is_conventional(subj):
        return
    if not is_unpushed(repo):
        print("dev-loop: HEAD is not conventional but already has upstream; not rewriting")
        return
    body = run_git(repo, "log", "-1", "--format=%b", check=False)
    new_subj = rewrite_subject(subj, key=key, commit_type=commit_type)
    msg = new_subj + (("\n\n" + body) if body else "") + "\n"
    run_git(repo, "commit", "--amend", "-m", msg)
    print(f"dev-loop: rewrote unpushed HEAD to {new_subj!r}")


def push_branch(repo: Path, branch: str) -> None:
    run_git(repo, "push", "-u", "origin", branch)


def pr_body(
    key: str,
    summary: str,
    spec: str,
    verdict: dict | None,
    verify_ok: bool,
    evidence: str = "",
) -> str:
    v = verdict or {}
    lines = [
        f"## Summary",
        f"{summary}",
        "",
        f"Jira: {key}",
        "",
        "## Test plan",
        "- [ ] Checkout this branch and run the project test command",
        "- [ ] Confirm verify log in the PR conversation if attached",
        f"- [ ] Verify exit was {'green' if verify_ok else 'unknown'}",
        "",
        "## Spec (excerpt)",
        (spec or "")[:2500] or "_no spec_",
        "",
        "## Review verdict",
        f"- verdict: {v.get('verdict', 'n/a')}",
        f"- summary: {v.get('summary', '')}",
    ]
    risks = v.get("risks") or []
    if risks:
        lines.append("- risks:")
        lines.extend(f"  - {r}" for r in risks)
    if evidence:
        lines.extend(["", "## Evidence", evidence[:4000]])
    return "\n".join(lines) + "\n"


def create_pr(
    repo: Path,
    title: str,
    body: str,
    gh_bin: str = "gh",
    base: str | None = None,
) -> int | None:
    cmd = [gh_bin, "pr", "create", "--title", title, "--body", body]
    if base:
        cmd.extend(["--base", base])
    proc = subprocess.run(cmd, cwd=str(repo), capture_output=True, text=True)
    out = (proc.stdout or "") + (proc.stderr or "")
    if proc.returncode != 0:
        raise RuntimeError(out.strip() or "gh pr create failed")
    m = re.search(r"/pull/(\d+)", out)
    if m:
        return int(m.group(1))
    return None


def ship_work(
    repo: Path,
    rels: list[str],
    key: str,
    summary: str,
    spec: str,
    verdict: dict | None,
    cfg,
    evidence: str = "",
) -> list[int]:
    """Stage loop-touched files, conventional commit, optional stacked PRs. Returns PR numbers."""
    msg = conventional_message(key, summary, spec.split("\n\n", 1)[0] if spec else "", commit_type=cfg.git.commit_type)
    if cfg.git.check_conventional:
        subj = msg.splitlines()[0]
        if not is_conventional(subj):
            rest = "\n".join(msg.splitlines()[1:])
            msg = rewrite_subject(subj, key=key, commit_type=cfg.git.commit_type)
            if rest.strip():
                msg = msg + "\n" + rest
            if not msg.endswith("\n"):
                msg += "\n"
    title = cfg.git.pr_title_pattern.format(type=cfg.git.commit_type, summary=summary, key=key)
    body = pr_body(key, summary, spec, verdict, True, evidence=evidence)
    prs: list[int] = []
    do_stack = bool(cfg.git.stack_prs and cfg.git.max_files_per_pr > 0 and len(rels) > cfg.git.max_files_per_pr)
    chunks = split_paths(rels, cfg.git.max_files_per_pr) if do_stack else [rels]
    root_branch = current_branch(repo)
    prev_base = default_branch(repo)
    for i, chunk in enumerate(chunks):
        if i > 0:
            name = f"{root_branch}-s{i + 1}"
            run_git(repo, "checkout", "-B", name)
        stage_paths(repo, chunk)
        committed = commit_if_needed(repo, msg if i == 0 else conventional_message(
            key, f"{summary} (stack {i + 1})", "", commit_type=cfg.git.commit_type
        ))
        if committed and cfg.git.rewrite_unpushed:
            maybe_rewrite_head(repo, key, cfg.git.commit_type, True)
        branch = current_branch(repo)
        if not cfg.git.push:
            continue
        push_branch(repo, branch)
        if cfg.git.create_pr:
            prn = create_pr(repo, title if i == 0 else f"{title} [{i + 1}/{len(chunks)}]", body, gh_bin=cfg.git.gh_bin, base=prev_base)
            if prn:
                prs.append(prn)
        prev_base = branch
    return prs
