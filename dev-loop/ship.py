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


def jira_issue_url(base_url: str, key: str) -> str:
    base = (base_url or "").rstrip("/")
    if not base or not key:
        return ""
    return f"{base}/browse/{key}"


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        s = (item or "").strip()
        if not s or s in seen:
            continue
        seen.add(s)
        out.append(s)
    return out


def pr_test_commands(repo: Path, cfg) -> list[str]:
    from verify_infer import infer_recipe, is_uv_project, python_tool_cmd

    cmds: list[str] = []
    uv = is_uv_project(repo)
    if uv:
        cmds.append("uv sync")
    recipe = infer_recipe(repo, cfg)
    if recipe:
        cmds.append(" ".join(recipe.test))
        if recipe.build and recipe.build != recipe.test:
            cmds.append(" ".join(recipe.build))
        if recipe.health:
            cmds.append(f"curl -sf {recipe.health}")
    pyproject = repo / "pyproject.toml"
    text = ""
    if pyproject.is_file():
        try:
            text = pyproject.read_text(encoding="utf-8")
        except OSError:
            text = ""
    if text:
        low = text.lower()
        if "[tool.ruff" in low or re.search(r"\bruff\b", text):
            cmds.append(" ".join(python_tool_cmd(repo, "ruff", "check", ".")))
        if "[tool.pyright" in low or re.search(r"\bpyright\b", text):
            cmds.append(" ".join(python_tool_cmd(repo, "pyright")))
        src = repo / "src"
        if src.is_dir():
            for main in sorted(src.glob("*/__main__.py")):
                pkg = main.parent.name
                if uv:
                    cmds.append(f"uv run python -m {pkg}")
                else:
                    cmds.append(f"python -m {pkg}")
    return _dedupe(cmds)


def pr_body_inputs(cfg, repo: Path, run: Path | None = None) -> dict:
    from config import load_secrets
    from lavish import decide_lavish

    jira = getattr(cfg, "jira", None)
    base = (getattr(jira, "base_url", "") or "").rstrip("/")
    if not base:
        base = (load_secrets().get("ATLASSIAN_BASE_URL") or "").rstrip("/")
    verify_log = ""
    if run is not None:
        vp = Path(run) / "verify.log"
        if vp.is_file():
            try:
                verify_log = vp.read_text(encoding="utf-8")
            except OSError:
                verify_log = ""
    from evidence import list_visual_evidence

    ev = getattr(cfg, "evidence", None)
    files = list_visual_evidence(run)
    require = True if ev is None else bool(getattr(ev, "require_visual", True))
    visual = require or bool(decide_lavish(cfg, repo).enabled) or bool(getattr(ev, "enabled", False))
    return {
        "jira_base": base,
        "test_commands": pr_test_commands(repo, cfg),
        "verify_log": verify_log,
        "visual": visual,
        "visual_files": [p.name for p in files],
    }


def pr_body(
    key: str,
    summary: str,
    spec: str,
    verdict: dict | None,
    verify_ok: bool,
    evidence: str = "",
    jira_base: str = "",
    test_commands: list[str] | None = None,
    verify_log: str = "",
    visual: bool = False,
    visual_files: list[str] | None = None,
) -> str:
    # Reviewers open Jira / spec.md. Do not paste the spec.
    _ = spec
    v = verdict or {}
    url = jira_issue_url(jira_base, key)
    jira_line = f"Jira: [{key}]({url})" if url else f"Jira: [{key}](/browse/{key})"
    blurb = (summary or "").strip() or f"Shipped {key}."
    lines = [
        "## Summary",
        blurb,
        "",
        jira_line,
        "",
        "## Test plan",
    ]
    cmds = [c.strip() for c in (test_commands or []) if (c or "").strip()]
    if cmds:
        for cmd in cmds:
            lines.append(f"- [ ] `{cmd}` — expect exit 0")
    else:
        lines.append("- [ ] Run the inferred verify recipe for this repo and confirm exit 0")
    if verify_ok:
        lines.append("- [ ] Confirm local verify exited 0")
    else:
        lines.append("- [ ] Confirm local verify status (not green at ship time)")
    lines.extend(["", "## Evidence"])
    log = (verify_log or "").strip()
    if log:
        lines.extend(["", "### Local verify", "", "```", log[:3000], "```"])
    else:
        lines.append("- Local verify: no verify.log in the run dir")
    shots = [str(x).strip() for x in (visual_files or []) if str(x).strip()]
    if shots:
        from evidence import visual_markdown

        lines.append("- Screenshots/video (all tickets). Text-only verify.log is not enough.")
        lines.append("")
        lines.extend(visual_markdown(shots).splitlines())
    elif visual:
        lines.append(
            "- Screenshots/video: required for every ticket (UI: screen/flow; backend: terminal "
            "snapshots of tests/run/curl). Write png/jpg/webp/gif/webm/mp4 under the run "
            "`evidence/` dir before ship."
        )
    else:
        lines.append("- Local verify: commands and exit codes from verify.log (require_visual off)")
    ev = (evidence or "").strip()
    if ev:
        lines.extend(["", ev[:4000]])
    review = str(v.get("verdict") or "n/a")
    if v.get("summary"):
        review = f"{review} — {v.get('summary')}"
    lines.extend(["", "## Review", review])
    risks = v.get("risks") or []
    if risks:
        lines.append("Risks:")
        lines.extend(f"- {r}" for r in risks)
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
    run: Path | None = None,
    jira_base: str = "",
    test_commands: list[str] | None = None,
    verify_log: str = "",
    visual: bool = False,
    visual_files: list[str] | None = None,
) -> list[int]:
    """Stage loop-touched files, conventional commit, optional stacked PRs. Returns PR numbers."""
    from evidence import comment_visual_evidence, list_visual_evidence, require_visual_evidence

    files = require_visual_evidence(cfg, run)
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
    extras = pr_body_inputs(cfg, repo, run)
    body = pr_body(
        key,
        summary,
        spec,
        verdict,
        True,
        evidence=evidence,
        jira_base=jira_base or extras["jira_base"],
        test_commands=test_commands if test_commands is not None else extras["test_commands"],
        verify_log=verify_log or extras["verify_log"],
        visual=visual or bool(extras["visual"]),
        visual_files=visual_files if visual_files is not None else extras.get("visual_files") or [p.name for p in files],
    )
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
                comment_visual_evidence(repo, prn, files or list_visual_evidence(run), gh_bin=cfg.git.gh_bin)
        prev_base = branch
    return prs
