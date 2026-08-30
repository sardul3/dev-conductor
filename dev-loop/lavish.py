#!/usr/bin/env python3
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from gitutil import repo_slug

UI_PACKAGES = {
    "react",
    "react-dom",
    "vue",
    "svelte",
    "@sveltejs/kit",
    "next",
    "nuxt",
    "@angular/core",
    "remix",
    "@remix-run/react",
    "astro",
    "gatsby",
    "preact",
    "solid-js",
}

UI_CONFIG_FILES = (
    "components.json",
    "angular.json",
    "next.config.js",
    "next.config.mjs",
    "next.config.ts",
    "nuxt.config.ts",
    "nuxt.config.js",
    "svelte.config.js",
    "astro.config.mjs",
)


@dataclass(frozen=True)
class LavishDecision:
    enabled: bool
    reason: str


def _package_is_ui(pkg: Path) -> bool:
    if not pkg.is_file():
        return False
    try:
        data = json.loads(pkg.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    if not isinstance(data, dict):
        return False
    deps: set[str] = set()
    for key in ("dependencies", "devDependencies", "peerDependencies"):
        block = data.get(key)
        if isinstance(block, dict):
            deps.update(str(k).lower() for k in block)
    return bool(UI_PACKAGES.intersection(deps))


def _ui_at(root: Path) -> bool:
    for name in UI_CONFIG_FILES:
        if (root / name).is_file():
            return True
    return _package_is_ui(root / "package.json")


def is_ui_repo(repo: Path) -> bool:
    root = Path(repo)
    if _ui_at(root):
        return True
    for rel in ("frontend", "web", "ui", "client", "apps/web"):
        nested = root.joinpath(*rel.split("/"))
        if nested.is_dir() and _ui_at(nested):
            return True
    return False


def _mode(raw: str) -> str:
    s = (raw or "auto").strip().lower()
    if s in ("true", "1", "yes"):
        return "on"
    if s in ("false", "0", "no"):
        return "off"
    if s not in ("on", "off", "auto"):
        return "auto"
    return s


def decide_lavish(cfg, repo: Path) -> LavishDecision:
    slug = repo_slug(repo)
    mode = _mode(getattr(getattr(cfg, "lavish", None), "enabled", None) or "auto")
    repos = getattr(getattr(cfg, "lavish", None), "repos", None) or {}
    if slug in repos:
        mode = _mode(str(repos[slug]))
    if mode == "off":
        return LavishDecision(False, f"off ({slug})")
    if mode == "on":
        return LavishDecision(True, f"on ({slug})")
    ui = is_ui_repo(repo)
    return LavishDecision(ui, f"auto:{'ui' if ui else 'not-ui'} ({slug})")
