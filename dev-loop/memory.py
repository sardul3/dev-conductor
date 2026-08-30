#!/usr/bin/env python3
from __future__ import annotations

import hashlib
from pathlib import Path

from gitutil import run_git
from paths import memory_dir

CONTRACT_GLOBS = (
    "*Controller*",
    "*Resource.java",
    "*Api.java",
    "*Client.java",
    "openapi*.yaml",
    "openapi*.yml",
    "openapi*.json",
    "*openapi*",
    "*.proto",
)


def fingerprint(repo: Path) -> str:
    head = run_git(repo, "rev-parse", "HEAD", check=False) or "NOHEAD"
    files = run_git(repo, "ls-files", "-z", check=False)
    h = hashlib.sha256()
    h.update(head.encode())
    names = [p for p in files.split("\0") if p]
    names.sort()
    for rel in names:
        path = repo / rel
        h.update(rel.encode())
        h.update(b"\0")
        try:
            h.update(path.read_bytes())
        except OSError:
            h.update(b"?")
    return h.hexdigest()


def index_is_fresh(repo: Path) -> bool:
    slug = repo.resolve().name
    mem = memory_dir(slug)
    fp_path = mem / "HASH"
    if not fp_path.is_file() or not (mem / "INDEX.md").is_file():
        return False
    return fp_path.read_text(encoding="utf-8").strip() == fingerprint(repo)


def _list_top(repo: Path) -> list[str]:
    names = []
    try:
        for p in sorted(repo.iterdir()):
            if p.name.startswith("."):
                continue
            names.append(p.name + ("/" if p.is_dir() else ""))
    except OSError:
        return []
    return names[:80]


def _contracts(repo: Path) -> str:
    tracked = run_git(repo, "ls-files", check=False).splitlines()
    picks: list[str] = []
    for rel in tracked:
        low = rel.lower()
        name = Path(rel).name
        if any(
            Path(rel).match(g) or Path(name).match(g) or g.replace("*", "") in low
            for g in CONTRACT_GLOBS
        ):
            if "/src/test/" in rel.replace("\\", "/") or "/tests/" in rel.replace("\\", "/"):
                continue
            picks.append(rel)
    chunks: list[str] = []
    for rel in picks[:24]:
        path = repo / rel
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        lines = text.splitlines()[:80]
        chunks.append(f"## {rel}\n" + "\n".join(lines))
    return "\n\n".join(chunks) if chunks else "(no public contract files detected)\n"


def regenerate(repo: Path) -> Path:
    slug = repo.resolve().name
    mem = memory_dir(slug)
    files = run_git(repo, "ls-files", check=False)
    n = len([x for x in files.splitlines() if x])
    head = run_git(repo, "rev-parse", "--short", "HEAD", check=False)
    stack = []
    for marker, label in (
        ("build.gradle", "gradle"),
        ("build.gradle.kts", "gradle"),
        ("pom.xml", "maven"),
        ("package.json", "npm"),
        ("go.mod", "go"),
        ("pyproject.toml", "python"),
        ("Cargo.toml", "rust"),
    ):
        if (repo / marker).exists():
            stack.append(label)
    index = (
        f"# {slug}\n\n"
        f"- HEAD: `{head}`\n"
        f"- tracked files: {n}\n"
        f"- stack: {', '.join(dict.fromkeys(stack)) or 'unknown'}\n\n"
        "## Top level\n\n"
        + "\n".join(f"- `{n}`" for n in _list_top(repo))
        + "\n"
    )
    (mem / "INDEX.md").write_text(index, encoding="utf-8")
    (mem / "contracts.md").write_text(_contracts(repo), encoding="utf-8")
    (mem / "HASH").write_text(fingerprint(repo) + "\n", encoding="utf-8")
    return mem


def load_or_build(repo: Path) -> Path:
    if not index_is_fresh(repo):
        return regenerate(repo)
    return memory_dir(repo.resolve().name)
