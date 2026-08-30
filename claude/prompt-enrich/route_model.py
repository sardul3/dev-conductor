#!/usr/bin/env python3
"""Detect CCR vs stock Claude Code and map a profile to --model ids."""

from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEFAULT_CATALOG = ROOT / "model-router.yaml"
LOCALHOST = re.compile(r"(127\.0\.0\.1|localhost)", re.I)
VISION = re.compile(r"\b(screenshot|screenshots|ui mock|wireframe|image|diagram|vision|vl)\b", re.I)
HEAVY = re.compile(r"\b(production|security|many files|multi-file|monorepo-wide)\b", re.I)
REASON = re.compile(r"\b(debug|investigate|design|architecture|deadlock|root cause)\b", re.I)
CODE = re.compile(r"\b(code|tests|patch|implement|refactor)\b", re.I)
PROFILES = ("fast", "code", "reason", "heavy", "vision")


def assert_ccr_free(model_id: str) -> str:
    slug = (model_id or "").strip()
    if not slug:
        raise ValueError("empty CCR model id")
    ok = slug.endswith(":free") or slug in {"OpenRouter/openrouter/free", "openrouter/free"}
    if not ok:
        raise ValueError(f"paid OpenRouter models are disabled: {slug}")
    return slug


@dataclass
class Route:
    backend: str
    profile: str
    primary: str
    fallback: str
    why: str = ""
    fallbacks: list[str] = field(default_factory=list)


def load_catalog(path: Path | None = None) -> dict:
    if path is not None:
        catalog_path = path
    elif os.environ.get("PROMPT_ENRICH_ROUTER"):
        catalog_path = Path(os.environ["PROMPT_ENRICH_ROUTER"])
    else:
        home_cat = Path.home() / ".claude" / "prompt-enrichment" / "model-router.yaml"
        catalog_path = home_cat if home_cat.is_file() else DEFAULT_CATALOG
    text = catalog_path.read_text(encoding="utf-8")
    return json.loads(text)


def _looks_local_gateway(value: str) -> bool:
    return bool(value) and bool(LOCALHOST.search(value))


def detect_backend(env: dict[str, str], settings: dict) -> str:
    explicit = (env.get("PROMPT_ENRICH_BACKEND") or "").strip().lower()
    if explicit in {"ccr", "anthropic"}:
        return explicit
    settings_env = settings.get("env") if isinstance(settings.get("env"), dict) else {}
    merged = {**settings_env, **env}
    for key in ("ANTHROPIC_BASE_URL", "ANTHROPIC_API_BASE_URL", "CLAUDE_AGENT_API_BASE_URL"):
        if _looks_local_gateway(str(merged.get(key) or "")):
            return "ccr"
    helper = str(settings.get("apiKeyHelper") or env.get("CLAUDE_CODE_API_KEY_HELPER") or "")
    if "claude-code-router" in helper:
        return "ccr"
    for key in ("CCR_CLAUDE_CODE_MODEL", "CODEXL_CLAUDE_CODE_MODEL"):
        if merged.get(key):
            return "ccr"
    return "anthropic"


def infer_profile(goal: str, context: str, output_format: str) -> str:
    blob = f"{goal}\n{context}\n{output_format}"
    if VISION.search(blob):
        return "vision"
    if HEAVY.search(blob):
        return "heavy"
    if REASON.search(blob):
        return "reason"
    if CODE.search(blob):
        return "code"
    return "fast"


def resolve(profile: str, backend: str, override: str | None = None, catalog: dict | None = None) -> Route:
    data = catalog or load_catalog()
    backend = backend if backend in {"ccr", "anthropic"} else "anthropic"
    why = f"profile={profile}"
    chosen = (profile or "code").strip().lower()
    ov = (override or "").strip().lower()
    aliases = data.get("aliases") or {}
    if ov:
        if ov in PROFILES:
            chosen = ov
            why = f"override profile {ov}"
        elif ov in aliases and isinstance(aliases[ov], dict) and aliases[ov].get(backend):
            table = data.get(backend) or {}
            row = table.get(chosen) or table.get("code") or {}
            primary = str(aliases[ov][backend])
            fallback = str(row.get("fallback") or primary)
            extra = [str(x) for x in (row.get("fallbacks") or []) if str(x) and str(x) != primary]
            if backend == "ccr":
                primary = assert_ccr_free(primary)
                fallback = assert_ccr_free(fallback)
                extra = [assert_ccr_free(x) for x in extra]
            return Route(
                backend=backend,
                profile=chosen,
                primary=primary,
                fallback=fallback,
                fallbacks=extra or [fallback],
                why=f"override alias {ov}",
            )
        else:
            why = f"unknown override {ov}; using {chosen}"
    if chosen not in PROFILES:
        chosen = "code"
        why = "unknown profile; default code"
    table = data.get(backend) or {}
    row = table.get(chosen) or table.get("code") or {}
    primary = str(row.get("primary") or "sonnet")
    fallback = str(row.get("fallback") or primary)
    extra = [str(x) for x in (row.get("fallbacks") or []) if str(x) and str(x) != primary]
    if not extra:
        extra = [fallback] if fallback != primary else []
    if backend == "ccr":
        primary = assert_ccr_free(primary)
        fallback = assert_ccr_free(fallback)
        extra = [assert_ccr_free(x) for x in extra]
        chain = data.get("ccr_free_chain") or []
        for item in chain:
            sid = str(item)
            if sid and sid != primary and sid not in extra:
                extra.append(assert_ccr_free(sid))
    return Route(backend=backend, profile=chosen, primary=primary, fallback=fallback, fallbacks=extra, why=why)


def load_settings(path: Path | None = None) -> dict:
    settings_path = path or Path.home() / ".claude" / "settings.json"
    if not settings_path.is_file():
        return {}
    try:
        return json.loads(settings_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def main() -> int:
    parser = argparse.ArgumentParser(description="Resolve prompt-enrich model ids")
    parser.add_argument("--profile", default="code")
    parser.add_argument("--override", default="")
    parser.add_argument("--backend", default="")
    parser.add_argument("--goal", default="")
    parser.add_argument("--context", default="")
    parser.add_argument("--format", dest="output_format", default="")
    args = parser.parse_args()
    settings = load_settings()
    backend = args.backend or detect_backend(dict(os.environ), settings)
    profile = args.profile
    if args.goal or args.context or args.output_format:
        profile = infer_profile(args.goal, args.context, args.output_format)
    route = resolve(profile, backend, args.override or None)
    print(json.dumps(asdict(route)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
