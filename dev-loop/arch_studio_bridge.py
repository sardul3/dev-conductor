#!/usr/bin/env python3
"""Arch Studio ↔ /dev-loop spec gate (Cursor-first)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from gitutil import repo_slug

ARCH_LABELS = frozenset(
    {
        "architecture",
        "arch",
        "integration",
        "system-integration",
        "azure",
        "kubernetes",
        "k8s",
        "infrastructure",
        "platform",
        "migration",
    }
)

ARCH_KEYWORDS = re.compile(
    r"\b("
    r"integrat(?:e|ion)|architect(?:ure|ural)?|system[\s-]design|"
    r"microservice|landing[\s-]zone|service[\s-]mesh|data[\s-]flow|"
    r"aks\b|kubernetes|bicep|terraform|draw\.?io"
    r")\b",
    re.I,
)

REPO_MARKERS = (
    "terraform",
    "infra",
    "infrastructure",
    "k8s",
    "kubernetes",
    "helm",
    "deploy",
    "iac",
    "bicep",
)


@dataclass(frozen=True)
class ArchStudioDecision:
    enabled: bool
    require_review: bool
    reason: str
    skill_root: str | None = None


def _mode(raw: str) -> str:
    s = (raw or "auto").strip().lower()
    if s in ("true", "1", "yes"):
        return "on"
    if s in ("false", "0", "no"):
        return "off"
    if s not in ("on", "off", "auto"):
        return "auto"
    return s


def skill_root() -> Path | None:
    here = Path(__file__).resolve()
    candidates = (
        here.parents[1] / "skills" / "arch-studio",
        Path.home() / ".cursor" / "skills" / "arch-studio",
        Path.home() / ".claude" / "skills" / "arch-studio",
    )
    for path in candidates:
        if (path / "SKILL.md").is_file():
            return path
    return None


def arch_output_dir(run: Path) -> Path:
    return run / "architecture"


def review_html(run: Path) -> Path:
    return arch_output_dir(run) / "review.html"


def manifest_path(run: Path) -> Path:
    return run / "arch_studio.json"


def load_manifest(run: Path) -> dict[str, Any] | None:
    path = manifest_path(run)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def write_manifest(run: Path, decision: ArchStudioDecision) -> None:
    root = decision.skill_root or (str(skill_root()) if skill_root() else None)
    payload = {
        "enabled": decision.enabled,
        "require_review": decision.require_review,
        "reason": decision.reason,
        "skill_root": root,
        "output_dir": str(arch_output_dir(run)),
        "review_html": str(review_html(run)),
        "model_glob": "*.arch.json",
    }
    manifest_path(run).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _issue_text(issue: dict[str, Any]) -> str:
    parts = [
        str(issue.get("summary") or ""),
        str(issue.get("description") or ""),
    ]
    labels = issue.get("labels") or []
    if isinstance(labels, list):
        parts.extend(str(x) for x in labels)
    return "\n".join(parts)


def _repo_signals(repo: Path) -> bool:
    root = Path(repo)
    for name in REPO_MARKERS:
        if (root / name).is_dir():
            return True
    for pattern in ("**/*.tf", "**/*.bicep", "**/Chart.yaml", "**/docker-compose*.yml"):
        if any(root.glob(pattern)):
            return True
    return False


def _ticket_signals(issue: dict[str, Any]) -> bool:
    labels = issue.get("labels") or []
    if isinstance(labels, list):
        lowered = {str(x).strip().lower() for x in labels}
        if ARCH_LABELS.intersection(lowered):
            return True
    return bool(ARCH_KEYWORDS.search(_issue_text(issue)))


def decide_arch_studio(cfg, repo: Path, issue: dict[str, Any] | None = None) -> ArchStudioDecision:
    block = getattr(cfg, "arch_studio", None)
    mode = _mode(getattr(block, "enabled", None) or "auto")
    repos = getattr(block, "repos", None) or {}
    require_default = bool(getattr(block, "require_review", True))
    slug = repo_slug(repo)
    root = skill_root()
    root_s = str(root) if root else None

    if slug in repos:
        mode = _mode(str(repos[slug]))
    if mode == "off":
        return ArchStudioDecision(False, False, f"off ({slug})", root_s)
    if mode == "on":
        return ArchStudioDecision(True, require_default, f"on ({slug})", root_s)

    issue = issue or {}
    ticket_hit = _ticket_signals(issue)
    repo_hit = _repo_signals(repo)
    if ticket_hit or repo_hit:
        bits = []
        if ticket_hit:
            bits.append("ticket")
        if repo_hit:
            bits.append("repo")
        return ArchStudioDecision(True, require_default, f"auto:{'+'.join(bits)} ({slug})", root_s)
    return ArchStudioDecision(False, False, f"auto:not-arch ({slug})", root_s)


def arch_review_required(run: Path) -> bool:
    manifest = load_manifest(run)
    if not manifest or not manifest.get("enabled"):
        return False
    return bool(manifest.get("require_review", True))


def arch_is_approved(run: Path) -> bool:
    return (run / "ARCH_APPROVED").is_file()


def _write_review_decisions(run: Path, *, disposition: str, note: str = "") -> None:
    out = arch_output_dir(run)
    out.mkdir(parents=True, exist_ok=True)
    payload = {
        "project_id": run.name,
        "version": "",
        "model_digest": "",
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
        "reviewer": "cursor",
        "overall_disposition": disposition,
        "decisions": [],
        "note": note,
    }
    (out / "review-decisions.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def approve_arch(run: Path, key: str = "") -> None:
    if not review_html(run).is_file():
        raise FileNotFoundError(
            f"dev-loop: build the architecture pack first — missing {review_html(run)}"
        )
    ticket = key or run.name
    (run / "ARCH_APPROVED").write_text("architecture approved\n", encoding="utf-8")
    _write_review_decisions(run, disposition="accepted")
    from progress import record

    record(run, "arch_studio", "approved", ticket=ticket, note="cursor")


def reject_arch(run: Path, key: str = "", note: str = "") -> None:
    ticket = key or run.name
    approved = run / "ARCH_APPROVED"
    if approved.is_file():
        approved.unlink()
    _write_review_decisions(run, disposition="rejected", note=note)
    from progress import record

    record(run, "arch_studio", "rejected", ticket=ticket, note=note or "cursor")


def arch_status(run: Path) -> dict[str, Any]:
    manifest = load_manifest(run) or {}
    return {
        "enabled": bool(manifest.get("enabled")),
        "require_review": bool(manifest.get("require_review", True)),
        "approved": arch_is_approved(run),
        "review_html": str(review_html(run)) if review_html(run).is_file() else None,
        "output_dir": str(arch_output_dir(run)),
        "skill_root": manifest.get("skill_root") or (str(skill_root()) if skill_root() else None),
        "reason": manifest.get("reason") or "",
    }
