#!/usr/bin/env python3
from __future__ import annotations

import re

TYPES = "feat|fix|docs|style|refactor|perf|test|chore|ci|build|revert"
SUBJ = re.compile(rf"^({TYPES})(\([A-Za-z0-9._/-]+\))?!?: .+")


def is_conventional(subject: str) -> bool:
    line = (subject or "").strip().splitlines()[0]
    return bool(SUBJ.match(line))


def rewrite_subject(subject: str, key: str = "", commit_type: str = "feat") -> str:
    line = (subject or "").strip().splitlines()[0]
    if is_conventional(line):
        if key and key not in line:
            return f"{line.rstrip()} ({key})"
        return line
    title = line
    for prefix in ("WIP:", "wip:", "WIP ", "wip "):
        if title.startswith(prefix):
            title = title[len(prefix) :].strip()
    title = title.rstrip(".")
    extra = f" ({key})" if key else ""
    return f"{commit_type}: {title}{extra}"
