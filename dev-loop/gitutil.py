#!/usr/bin/env python3
from __future__ import annotations

import re
import subprocess
from pathlib import Path


def run_git(repo: Path, *args: str, check: bool = True) -> str:
    cmd = ["git", "-C", str(repo), *args]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if check and proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()
        raise RuntimeError(err or f"git {' '.join(args)} failed")
    return (proc.stdout or "").strip()


def is_git_repo(path: Path) -> bool:
    try:
        run_git(path, "rev-parse", "--is-inside-work-tree")
        return True
    except RuntimeError:
        return False


def github_remote(repo: Path) -> str | None:
    raw = run_git(repo, "remote", "-v", check=False)
    for line in raw.splitlines():
        low = line.lower()
        if "github.com" in low:
            parts = line.split()
            if len(parts) >= 2:
                return parts[1]
    return None


def github_https_repo(remote: str | None) -> str:
    raw = (remote or "").strip()
    if not raw:
        return ""
    m = re.search(r"github\.com[:/]([^/]+)/([^/\s]+)", raw, re.I)
    if not m:
        return ""
    owner, name = m.group(1), m.group(2)
    if name.endswith(".git"):
        name = name[:-4]
    name = name.rstrip("/")
    if not owner or not name:
        return ""
    return f"https://github.com/{owner}/{name}"


def github_pr_url(remote: str | None, number: int | None) -> str:
    if number is None:
        return ""
    base = github_https_repo(remote)
    if not base:
        return ""
    return f"{base}/pull/{int(number)}"


def default_branch(repo: Path) -> str:
    name = run_git(repo, "symbolic-ref", "refs/remotes/origin/HEAD", check=False)
    if name.startswith("refs/remotes/origin/"):
        return name.rsplit("/", 1)[-1]
    for cand in ("main", "master"):
        out = run_git(repo, "show-ref", "--verify", f"refs/heads/{cand}", check=False)
        if out:
            return cand
    return run_git(repo, "rev-parse", "--abbrev-ref", "HEAD")


def current_branch(repo: Path) -> str:
    return run_git(repo, "rev-parse", "--abbrev-ref", "HEAD")


def under_dev(path: Path, dev_root: Path) -> bool:
    try:
        path.resolve().relative_to(dev_root.expanduser().resolve())
        return True
    except ValueError:
        return False


def cwd_is_dev_root(cwd: Path, dev_root: Path) -> bool:
    try:
        return cwd.resolve() == dev_root.expanduser().resolve()
    except OSError:
        return False


def repo_slug(repo: Path) -> str:
    return repo.resolve().name


def denylisted(repo: Path, patterns: list[str]) -> bool:
    text = str(repo.resolve())
    name = repo.resolve().name
    for pat in patterns:
        if not pat:
            continue
        if pat in text or name == pat or text.endswith("/" + pat.strip("*")):
            return True
    return False


def is_unpushed(repo: Path) -> bool:
    up = run_git(repo, "rev-parse", "--abbrev-ref", "@{upstream}", check=False)
    return not bool(up)

