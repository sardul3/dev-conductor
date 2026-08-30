#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

TEMPLATES = Path(__file__).resolve().parent / "eval_templates"
MAP = {
    "LAB-1": "tests/test_health.py",
    "LAB-2": "tests/test_create.py",
    "LAB-3": "tests/test_list.py",
    "LAB-4": "tests/test_get.py",
    "LAB-5": "tests/test_complete.py",
}


def run_stage(stage: str, key: str, repo: Path, run: Path, cfg: Any, **kwargs: Any) -> None:
    if stage == "spec":
        issue = kwargs.get("issue") or {}
        spec = (
            "# Spec "
            + key
            + "\n\n**Seam:** public handle(method, path, body) (not internals).\n\n## Summary\n"
            + str(issue.get("summary") or "")
            + "\n\n## Behavior\n"
            + str(issue.get("description") or "")
            + "\n\n## Non-goals\nAuth, disk persistence, OpenAPI file.\n"
        )
        (run / "spec.md").write_text(spec, encoding="utf-8")
        return
    if stage == "test_writer":
        rel = MAP.get(key)
        if not rel:
            raise SystemExit("no eval tests for " + key)
        src = TEMPLATES / rel
        dest = repo / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        (repo / "tests" / "__init__.py").write_text("", encoding="utf-8")
        return
    if stage == "writer":
        shutil.copy2(TEMPLATES / "app.py", repo / "app.py")
        return
    if stage == "simplify":
        return
    if stage == "review":
        verdict = {
            "verdict": cfg.review.default_verdict,
            "summary": "eval adapter review for " + key,
            "risks": [],
        }
        (run / "verdict.json").write_text(json.dumps(verdict, indent=2) + "\n", encoding="utf-8")
