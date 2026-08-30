#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, TextIO

from gitutil import denylisted, is_git_repo
from ship import slugify

CREATE_ID = "__create__"
DEFAULT_SKIP = [
    "node_modules",
    ".git",
    "dist",
    "build",
    "target",
    "__pycache__",
    "venv",
    ".venv",
    ".tox",
    "coverage",
    ".mypy_cache",
    ".pytest_cache",
]


def _skip_name(name: str, skip: set[str]) -> bool:
    if name in skip:
        return True
    if name.startswith(".") and name not in {".", ".."}:
        return True
    return False


def list_candidates(
    root: Path,
    max_depth: int = 3,
    skip: list[str] | None = None,
    denylist: list[str] | None = None,
    allowlist: list[str] | None = None,
    max_choices: int = 40,
) -> list[dict[str, Any]]:
    root = root.expanduser().resolve()
    skip_set = set(skip or DEFAULT_SKIP)
    deny = list(denylist or [])
    allow = list(allowlist or [])
    found: list[dict[str, Any]] = []
    if not root.is_dir() or max_depth < 1:
        return []

    stack: list[tuple[Path, int]] = [(root, 0)]
    while stack:
        dirpath, depth = stack.pop()
        if depth >= max_depth:
            continue
        try:
            children = sorted((p for p in dirpath.iterdir() if p.is_dir()), key=lambda p: p.name.lower())
        except OSError:
            continue
        for child in reversed(children):
            if child.is_symlink():
                continue
            if _skip_name(child.name, skip_set):
                continue
            if denylisted(child, deny):
                continue
            rel = str(child.relative_to(root))
            slug = child.name
            if allow and slug not in allow and rel not in allow:
                stack.append((child, depth + 1))
                continue
            git_here = (child / ".git").exists()
            found.append(
                {
                    "id": str(child),
                    "path": str(child),
                    "rel": rel,
                    "slug": slug,
                    "depth": depth + 1,
                    "kind": "git" if git_here else "folder",
                    "label": f"{rel} ({'git' if git_here else 'folder'})",
                }
            )
            stack.append((child, depth + 1))

    found.sort(key=lambda c: (0 if c["kind"] == "git" else 1, c["rel"].lower()))
    return found[: max(1, int(max_choices))]


def candidates_payload(cfg: Any) -> dict[str, Any]:
    pick = getattr(cfg, "repo_pick", None)
    max_depth = int(getattr(pick, "max_depth", 3) or 3)
    max_choices = int(getattr(pick, "max_choices", 40) or 40)
    skip = list(getattr(pick, "skip", None) or DEFAULT_SKIP)
    items = list_candidates(
        cfg.dev_root,
        max_depth=max_depth,
        skip=skip,
        denylist=list(cfg.denylist or []),
        allowlist=list(cfg.allowlist or []),
        max_choices=max_choices,
    )
    cwd = Path.cwd().resolve()
    for c in items:
        try:
            cpath = Path(c["path"]).resolve()
            if cwd == cpath or cwd.is_relative_to(cpath):
                c["cwd"] = True
                if "[cwd]" not in c["label"]:
                    c["label"] = c["label"] + " [cwd]"
        except (OSError, ValueError):
            pass
    return {
        "dev_root": str(cfg.dev_root.expanduser()),
        "max_depth": max_depth,
        "create_id": CREATE_ID,
        "create_label": "Create a new folder/repo under " + str(cfg.dev_root),
        "candidates": items,
    }


def init_local_repo(dev_root: Path, name: str) -> Path:
    slug = slugify(name, max_len=60)
    dest = dev_root.expanduser().resolve() / slug
    dest.mkdir(parents=True, exist_ok=True)
    if not (dest / ".git").exists():
        subprocess.check_call(["git", "init", "-q", "-b", "main"], cwd=dest)
    readme = dest / "README.md"
    if not readme.is_file():
        readme.write_text("# " + slug + "\n", encoding="utf-8")
        subprocess.check_call(["git", "add", "README.md"], cwd=dest)
        subprocess.check_call(["git", "config", "user.email", "devloop@local"], cwd=dest)
        subprocess.check_call(["git", "config", "user.name", "dev-loop"], cwd=dest)
        status = subprocess.run(["git", "status", "--porcelain"], cwd=dest, capture_output=True, text=True)
        if status.stdout.strip():
            subprocess.check_call(["git", "commit", "-qm", "chore: initial repo"], cwd=dest)
    return dest


def maybe_gh_create(repo: Path, private: bool, gh_bin: str) -> None:
    proc = subprocess.run(
        [
            gh_bin,
            "repo",
            "create",
            repo.name,
            "--private" if private else "--public",
            "--source",
            str(repo),
            "--remote",
            "origin",
            "--push",
        ],
        cwd=str(repo),
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()
        print("dev-loop: gh repo create skipped/failed: " + err)
        print("          create it later: gh repo create " + repo.name + " --source " + str(repo) + " --private --push")


def init_repo(cfg: Any, name: str) -> Path:
    pick = getattr(cfg, "repo_pick", None)
    dest = init_local_repo(cfg.dev_root, name)
    if pick is None or bool(getattr(pick, "gh_create", True)):
        maybe_gh_create(dest, private=bool(getattr(pick, "create_private", True) if pick else True), gh_bin=cfg.git.gh_bin)
    return dest


def _prompt(cands: list[dict[str, Any]], create_label: str, stdin: TextIO, stdout: TextIO) -> str:
    stdout.write("Where should this ticket land?\n")
    for i, c in enumerate(cands, 1):
        stdout.write(f"  {i}. {c['label']}\n")
    stdout.write(f"  {len(cands) + 1}. {create_label}\n")
    stdout.write("Select number: ")
    stdout.flush()
    raw = (stdin.readline() or "").strip()
    if not raw.isdigit():
        raise SystemExit("dev-loop: expected a number")
    n = int(raw)
    if n == len(cands) + 1:
        return CREATE_ID
    if n < 1 or n > len(cands):
        raise SystemExit("dev-loop: choice out of range")
    return str(cands[n - 1]["path"])


def resolve_repo(cfg: Any, explicit: str | Path | None, *, require) -> Path:
    from conductor import require_repo

    if explicit:
        return require_repo(Path(str(explicit)).expanduser().resolve(), cfg)
    pick = getattr(cfg, "repo_pick", None)
    # Eval / scripts: no picker. Cursor workspace is often the wrong git repo — always ask.
    if pick is not None and not bool(getattr(pick, "ask_when_cwd_not_repo", True)):
        return require_repo(Path.cwd().resolve(), cfg)
    if bool(getattr(getattr(cfg, "runtime", None), "builtin_adapters", False)):
        return require_repo(Path.cwd().resolve(), cfg)
    payload = candidates_payload(cfg)
    if not sys.stdin.isatty():
        sys.stdout.write(json.dumps(payload, indent=2) + "\n")
        sys.stderr.write(
            "dev-loop: cwd is not a git repo under ~/dev. "
            "Ask the user which candidate to use (dropdown), or create a new one.\n"
            "Then: python3 ~/.claude/hooks/dev-loop/cli.py start KEY --repo PATH\n"
            "   or: python3 ~/.claude/hooks/dev-loop/cli.py init-repo NAME\n"
        )
        raise SystemExit(2)
    chosen = _prompt(payload["candidates"], payload["create_label"], sys.stdin, sys.stderr)
    if chosen == CREATE_ID:
        sys.stderr.write("New folder name under " + payload["dev_root"] + ": ")
        sys.stderr.flush()
        name = (sys.stdin.readline() or "").strip()
        if not name:
            raise SystemExit("dev-loop: name required")
        dest = init_repo(cfg, name)
        return require_repo(dest, cfg)
    path = Path(chosen)
    if not is_git_repo(path):
        dest = init_local_repo(path.parent, path.name)
        pick = getattr(cfg, "repo_pick", None)
        if pick is None or bool(getattr(pick, "gh_create", True)):
            maybe_gh_create(dest, private=bool(getattr(pick, "create_private", True) if pick else True), gh_bin=cfg.git.gh_bin)
        return require_repo(dest, cfg)
    return require_repo(path, cfg)
