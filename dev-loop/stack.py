#!/usr/bin/env python3
from __future__ import annotations


def split_paths(paths: list[str], max_files: int) -> list[list[str]]:
    files = [p for p in paths if p]
    if max_files <= 0 or len(files) <= max_files:
        return [files] if files else [[]]
    return [files[i : i + max_files] for i in range(0, len(files), max_files)]
