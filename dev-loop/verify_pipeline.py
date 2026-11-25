#!/usr/bin/env python3
"""Pre-production gates for one ticket. Deploy, release, and post-release stay after merge.

Procedures borrowed from swe-agent-suite and mac-ai-setup are named in skills/verify-pipeline.
"""
from __future__ import annotations

import json
import shlex
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

from quality import parse_pit_killed_pct

RISKS = ("safe", "normal", "sensitive")
B_ORDER = (
    "unit",
    "component",
    "integration",
    "functional",
    "acceptance",
    "regression",
    "property",
    "fuzz",
    "coverage",
    "pit",
    "benchmark",
)
C_ORDER = ("nondocher_health", "docker_health", "functional_run", "smoke", "browser")
SKIP_DIRS = {".git", "node_modules", "venv", ".venv", "target", "build", "dist", "__pycache__"}
UI_EXT = (".tsx", ".jsx", ".vue", ".css", ".scss", ".html", ".svelte")
SOURCE_EXT = {".py", ".java", ".kt", ".ts", ".tsx", ".js", ".go", ".kts"}
PROTECTED_TOKENS = ("auth", "payment", "billing", "migrate", "migration", "privacy")


@dataclass
class VerifyInput:
    risk_class: str = "normal"
    explicit_risk: str = ""
    labels: tuple[str, ...] = ()
    changed: tuple[str, ...] = ()
    changed_lines: int = 0
    spec: str = ""
    human_text: str = ""
    fix_cap: int = 2
    tiny_max_lines: int = 40
    coverage_min_pct: float = 80.0
    pit_min_pct: float = 75.0
    commands: dict[str, str] = field(default_factory=dict)
    hot_paths: tuple[str, ...] = ("**/hot/**", "**/perf/**", "*benchmark*", "*HotPath*")
    protected_paths: tuple[str, ...] = (
        "**/auth/**",
        "**/payment/**",
        "**/billing/**",
        "**/migrate/**",
        "**/migration/**",
        "**/privacy/**",
    )
    fail_closed: bool = True
    dep_diff: str = ""


@dataclass
class Check:
    name: str
    stage: str
    required: bool
    kind: str = "builtin"
    command: str = ""
    autofix: bool = False
    status: str = "planned"
    detail: str = ""
    exit_code: int | None = None
    log: str = ""


@dataclass
class PipelineResult:
    risk: str
    checks: list[Check]
    exit_code: int
    pr_allowed: bool
    reason: str
    bundle: Path | None = None
    waiting_human: bool = False


def is_test_path(path: str) -> bool:
    low = path.replace("\\", "/").lower()
    name = Path(low).name
    if low.startswith("tests/") or low.startswith("test/") or "/tests/" in f"/{low}" or "/test/" in f"/{low}":
        return True
    if name.startswith("test_") or name.endswith("_test.py") or name.endswith("test.java") or name.endswith("tests.java"):
        return True
    return False


def is_protected(path: str, _patterns: tuple[str, ...] | list[str] = ()) -> bool:
    parts = path.replace("\\", "/").lower().split("/")
    return any(part in PROTECTED_TOKENS for part in parts)


def is_hot(path: str, text: str = "") -> bool:
    rel = path.replace("\\", "/").lower()
    padded = f"/{rel}"
    if "/hot/" in padded or "/perf/" in padded:
        return True
    if "benchmark" in rel or "hotpath" in rel:
        return True
    return "hot-path" in text or "@HotPath" in text


def is_ui(path: str) -> bool:
    return path.lower().endswith(UI_EXT)


def is_spec_path(path: str) -> bool:
    name = Path(path).name.lower()
    return name.startswith("openapi") or name.endswith(".proto") or name == "api.md"


def is_public_impl(path: str) -> bool:
    if is_test_path(path) or is_spec_path(path):
        return False
    low = path.lower()
    return any(hint in low for hint in ("controller", "resource", "handler", "routes"))


def resolve_risk(inp: VerifyInput) -> str:
    explicit = (inp.explicit_risk or "").strip().lower()
    if explicit in RISKS:
        return explicit
    if any(is_protected(path, inp.protected_paths) for path in inp.changed):
        return "sensitive"
    for label in inp.labels:
        text = str(label).lower().replace("risk:", "").replace("risk-", "").strip()
        if text in RISKS:
            return text
    risk = (inp.risk_class or "normal").strip().lower()
    return risk if risk in RISKS else "normal"


def repo_boots(repo: Path, inp: VerifyInput) -> bool:
    cmds = inp.commands or {}
    if any(cmds.get(name) for name in ("nondocher", "docker", "health", "smoke")):
        return True
    return any((repo / name).is_file() for name in ("docker-compose.yml", "compose.yml", "Procfile"))


def _walk(repo: Path) -> list[Path]:
    found: list[Path] = []
    if not repo.is_dir():
        return found
    for path in repo.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.relative_to(repo).parts):
            continue
        found.append(path)
    return found


def _rel(repo: Path, path: Path) -> str:
    return path.relative_to(repo).as_posix()


def kind_files(repo: Path, changed: tuple[str, ...] | list[str], token: str) -> list[str]:
    parents = {str(Path(item).parent).replace("\\", "/") for item in changed}
    hits: list[str] = []
    for path in _walk(repo):
        if token not in path.name.lower():
            continue
        rel = _rel(repo, path)
        parent = str(Path(rel).parent).replace("\\", "/")
        if parent in parents:
            hits.append(rel)
    return sorted(hits)


def banned_comment_hits(text: str) -> list[str]:
    import re

    allow = re.compile(r"lint:allow-comment:\s*\S+")
    ban = re.compile(r"\b(TODO|FIXME|XXX|HACK)\b")
    lines = text.splitlines()
    hits: list[str] = []
    for index, line in enumerate(lines):
        if not ban.search(line):
            continue
        prev = lines[index - 1] if index else ""
        if allow.search(line) or allow.search(prev):
            continue
        hits.append(line.strip())
    return hits


def antipattern_hits(text: str) -> list[str]:
    import re

    patterns = (
        re.compile(r"except\s*:\s*(?:pass|\.\.\.)"),
        re.compile(r"except\s+Exception\s*:\s*(?:pass|\.\.\.)"),
        re.compile(r"printStackTrace\s*\("),
        re.compile(r"catch\s*\([^)]*\)\s*\{\s*\}"),
    )
    return [pat.pattern for pat in patterns if pat.search(text)]


def api_doc_problem(changed: list[str] | tuple[str, ...], repo_files: list[str]) -> str:
    specs = [path for path in repo_files if is_spec_path(path)]
    impl = [path for path in changed if is_public_impl(path)]
    if impl and specs and not any(is_spec_path(path) for path in changed):
        return f"public contract changed without spec update: {specs[0]}"
    return ""


def parse_diff_coverage(text: str) -> float | None:
    import re

    match = re.search(r"diff coverage[:\s]+(\d+(?:\.\d+)?)\s*%", text, re.I)
    if not match:
        return None
    return float(match.group(1))


def introduced_packages(diff: str) -> set[str]:
    import re

    found: set[str] = set()
    for line in (diff or "").splitlines():
        if not line.startswith("+") or line.startswith("+++"):
            continue
        body = line[1:].strip()
        req = re.match(r"([A-Za-z0-9_.-]+)==", body)
        if req:
            found.add(req.group(1).lower())
            continue
        quoted = re.search(r'"([A-Za-z0-9_.-]+)"\s*:\s*"', body)
        if quoted:
            found.add(quoted.group(1).lower())
        gradle = re.search(r"['\"][A-Za-z0-9_.-]+:([A-Za-z0-9_.-]+):", body)
        if gradle:
            found.add(gradle.group(1).lower())
    return found


def classify_cves(
    findings: list[dict],
    baseline_ids: set[str],
    introduced: set[str],
) -> tuple[list[dict], list[dict]]:
    base = {item.upper() for item in baseline_ids}
    fresh_pkgs = {item.lower() for item in introduced}
    failing: list[dict] = []
    recorded: list[dict] = []
    for finding in findings:
        fid = str(finding.get("id") or finding.get("cve") or "").upper()
        pkg = str(finding.get("package") or finding.get("packageName") or finding.get("moduleName") or "").lower()
        introduced_hit = bool(pkg) and pkg in fresh_pkgs
        in_diff = finding.get("in_diff")
        if introduced_hit or in_diff is True or (fid not in base and in_diff is not False):
            failing.append(finding)
        else:
            recorded.append(finding)
    return failing, recorded


def sensitive_spec_gaps(spec: str) -> list[str]:
    text = (spec or "").lower()
    gaps: list[str] = []
    if "threat model" not in text:
        gaps.append("threat model")
    if "pen test" not in text and "penetration test" not in text:
        gaps.append("pen test")
    return gaps


def human_name(text: str) -> str | None:
    name = " ".join((text or "").split())
    if not name or name.lower() in {"auto", "agent", "dev-loop"}:
        return None
    return name


def should_diagrams(risk: str, changed_lines: int, tiny_max: int) -> bool:
    if risk == "safe":
        return False
    return changed_lines > tiny_max


def _check(name: str, stage: str, required: bool = True, kind: str = "builtin", command: str = "", autofix: bool = False) -> Check:
    return Check(name=name, stage=stage, required=required, kind=kind, command=command, autofix=autofix)


def plan_gates(repo: Path, inp: VerifyInput) -> list[Check]:
    risk = resolve_risk(inp)
    commands = dict(inp.commands or {})
    checks: list[Check] = [
        _check("api_doc", "A"),
        _check("banned_comments", "A"),
        _check("antipattern", "A"),
    ]
    if commands.get("contract") or any(is_spec_path(path) for path in inp.changed):
        checks.append(_check("contract", "A", kind="command", command=commands.get("contract", "")))
    if commands.get("lint"):
        checks.append(_check("lint", "A", kind="command", command=commands["lint"]))
    if commands.get("architecture"):
        checks.append(_check("architecture", "A", kind="command", command=commands["architecture"]))
    if risk == "sensitive":
        checks.append(_check("threat_model", "A", kind="spec"))
        checks.append(_check("pen_test_input", "A", kind="spec"))

    suite_names = ("unit", "component", "integration", "functional", "acceptance", "regression")
    for name in suite_names:
        if name == "unit" or commands.get(name):
            checks.append(_check(name, "B", kind="command", command=commands.get(name, "")))

    for token, key in (("property", "property"), ("fuzz", "fuzz")):
        files = kind_files(repo, inp.changed, token)
        if files or risk == "sensitive":
            cmd = commands.get(key) or ("python3 -m pytest " + " ".join(files) if files else "")
            checks.append(_check(key, "B", kind="command", command=cmd))

    checks.append(_check("coverage", "B", kind="command", command=commands.get("coverage", "")))
    if risk != "safe":
        checks.append(_check("pit", "B", kind="command", command=commands.get("pit", "")))
    if any(is_hot(path) for path in inp.changed):
        checks.append(_check("benchmark", "B", kind="command", command=commands.get("benchmark", "")))

    if risk != "safe" and repo_boots(repo, inp):
        if commands.get("nondocher"):
            checks.append(_check("nondocher_health", "C", kind="command", command=commands["nondocher"]))
        if commands.get("docker") or (repo / "docker-compose.yml").is_file() or (repo / "compose.yml").is_file():
            checks.append(_check("docker_health", "C", kind="command", command=commands.get("docker", "")))
        if commands.get("functional") or commands.get("functional_run"):
            checks.append(_check("functional_run", "C", kind="command", command=commands.get("functional") or commands.get("functional_run", "")))
        checks.append(_check("smoke", "C", kind="command", command=commands.get("smoke") or commands.get("health", "")))
    if risk != "safe" and any(is_ui(path) for path in inp.changed):
        checks.append(_check("browser", "C", kind="command", command=commands.get("browser", "")))

    if risk != "safe":
        checks.append(_check("security", "D", kind="command", command=commands.get("security", "")))
    checks.append(_check("smells", "E", required=False, autofix=risk != "sensitive"))
    return checks


def fixer_violation(
    defining_before: dict[str, str],
    defining_after: dict[str, str],
    ticket_files: set[str],
    edited_files: set[str],
    floors_before: dict[str, float],
    floors_after: dict[str, float],
) -> str:
    for path, digest in defining_before.items():
        if defining_after.get(path) != digest:
            return f"defining test edited: {path}"
    parents = {str(Path(path).parent).replace("\\", "/") for path in ticket_files}
    for path in edited_files:
        if path in ticket_files:
            continue
        parent = str(Path(path).parent).replace("\\", "/")
        if parent in parents:
            continue
        return f"expanded past ticket: {path}"
    for key, old in floors_before.items():
        new = float(floors_after.get(key, old))
        if new < float(old):
            return f"weakened threshold: {key}"
    return ""


def smell_actions(
    findings: list[dict],
    touched: set[str],
    risk: str,
    cap: int,
) -> tuple[list[dict], list[dict]]:
    intents = [item for item in findings if item.get("path") not in touched]
    if risk == "sensitive":
        return [], intents
    fixes: list[dict] = []
    for item in findings:
        path = str(item.get("path") or "")
        if path not in touched or is_test_path(path) or item.get("kind") != "trailing_ws":
            continue
        if len(fixes) >= max(0, cap):
            break
        fixes.append(item)
    return fixes, intents


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _repo_files(repo: Path) -> list[str]:
    return [_rel(repo, path) for path in _walk(repo)]


def _load_baseline(repo: Path) -> set[str]:
    path = repo / ".devloop" / "cve-baseline.json"
    if not path.is_file():
        return set()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return set()
    if isinstance(data, dict):
        return {str(item).upper() for item in data.get("ids") or []}
    if isinstance(data, list):
        return {str(item).upper() for item in data}
    return set()


def _snyk_findings(raw: str, introduced: set[str]) -> list[dict]:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []
    findings: list[dict] = []
    for vuln in data.get("vulnerabilities") or []:
        pkg = str(vuln.get("package") or vuln.get("packageName") or vuln.get("moduleName") or "")
        fid = str(vuln.get("id") or vuln.get("cve") or "")
        findings.append({
            "id": fid,
            "package": pkg,
            "in_diff": pkg.lower() in introduced or bool(vuln.get("in_diff")),
        })
    return findings


def _strip_trailing(text: str) -> str:
    body = "\n".join(line.rstrip() for line in text.splitlines())
    if text.endswith("\n"):
        body += "\n"
    return body


def _find_smells(repo: Path) -> list[dict]:
    findings: list[dict] = []
    for path in _walk(repo):
        if path.suffix.lower() not in SOURCE_EXT:
            continue
        text = _read(path)
        if any(line.endswith(" ") or line.endswith("\t") for line in text.splitlines()):
            findings.append({"path": _rel(repo, path), "kind": "trailing_ws"})
    return findings


def _run_cmd(check: Check, repo: Path, runner, timeout: int) -> None:
    if not check.command.strip():
        check.status = "fail"
        check.detail = f"{check.name}: no command (fail closed)"
        check.exit_code = 1
        return
    try:
        cmd = shlex.split(check.command)
    except ValueError as exc:
        check.status = "fail"
        check.detail = str(exc)
        check.exit_code = 1
        return
    rc, out = runner(repo, cmd, timeout)
    check.exit_code = rc
    check.log = out or ""
    check.detail = f"$ {check.command}\nexit {rc}"
    check.status = "pass" if rc == 0 else "fail"


def _apply_builtin(check: Check, repo: Path, inp: VerifyInput, risk: str) -> str:
    files = _repo_files(repo)
    if check.name == "api_doc":
        problem = api_doc_problem(inp.changed, files)
        check.status = "fail" if problem else "pass"
        check.detail = problem or "api doc diff clean"
        return ""
    if check.name == "banned_comments":
        hits: list[str] = []
        for rel in inp.changed:
            hits.extend(banned_comment_hits(_read(repo / rel)))
        check.status = "fail" if hits else "pass"
        check.detail = "; ".join(hits) or "no banned comments"
        return ""
    if check.name == "antipattern":
        hits = []
        for rel in inp.changed:
            if is_test_path(rel):
                continue
            hits.extend(antipattern_hits(_read(repo / rel)))
        check.status = "fail" if hits else "pass"
        check.detail = "; ".join(hits) or "no antipatterns"
        return ""
    if check.name in {"threat_model", "pen_test_input"}:
        gaps = sensitive_spec_gaps(inp.spec)
        wanted = "threat model" if check.name == "threat_model" else "pen test"
        missing = wanted in gaps
        check.status = "fail" if missing else "pass"
        check.detail = f"spec missing {wanted}" if missing else f"spec has {wanted}"
        return ""
    check.status = "pass"
    return ""


def _coverage_gate(check: Check, inp: VerifyInput) -> None:
    if check.status != "pass":
        check.detail = check.detail or "coverage command failed"
        return
    pct = parse_diff_coverage(check.log)
    if pct is None:
        check.status = "fail"
        check.detail = "coverage: not a diff report (fail closed)"
        return
    if pct < float(inp.coverage_min_pct):
        check.status = "fail"
        check.detail = f"diff coverage {pct}% (min {inp.coverage_min_pct}%)"
        return
    check.detail = f"diff coverage {pct}% (min {inp.coverage_min_pct}%)"


def _pit_gate(check: Check, inp: VerifyInput) -> None:
    if check.status != "pass" and not check.log:
        check.detail = check.detail or "pit: no command (fail closed)"
        check.status = "fail"
        return
    killed = parse_pit_killed_pct(check.log or "")
    if killed is None:
        check.status = "fail"
        check.detail = "pit: could not parse score (fail closed)"
        return
    if killed < float(inp.pit_min_pct):
        check.status = "fail"
        check.detail = f"pit killed {killed}% (min {inp.pit_min_pct}%)"
        return
    check.status = "pass"
    check.detail = f"pit killed {killed}% (min {inp.pit_min_pct}%)"


def _security_gate(check: Check, repo: Path, inp: VerifyInput) -> dict:
    if not check.command.strip():
        check.status = "fail"
        check.detail = "security: scanner missing (fail closed)"
        return {"failing": [], "recorded": []}
    if check.status != "pass" and not check.log.strip():
        check.status = "fail"
        check.detail = check.detail or "security scanner failed"
        return {"failing": [], "recorded": []}
    introduced = introduced_packages(inp.dep_diff)
    findings = _snyk_findings(check.log, introduced)
    if not findings and check.exit_code not in (0, None):
        check.status = "fail"
        check.detail = "security: unreadable scanner output (fail closed)"
        return {"failing": [], "recorded": []}
    failing, recorded = classify_cves(findings, _load_baseline(repo), introduced)
    report = {"failing": failing, "recorded": recorded}
    if failing:
        check.status = "fail"
        check.detail = "new cves: " + ", ".join(str(item.get("id")) for item in failing)
    else:
        check.status = "pass"
        check.detail = f"recorded baseline cves: {len(recorded)}"
    return report


def _ordered(checks: list[Check], stage: str, order: tuple[str, ...]) -> list[Check]:
    wanted = [item for item in checks if item.stage == stage]
    rank = {name: index for index, name in enumerate(order)}
    return sorted(wanted, key=lambda item: rank.get(item.name, 50))


def _failed(checks: list[Check]) -> list[Check]:
    return [item for item in checks if item.required and item.status == "fail"]


def _write_result(dest: Path, result: PipelineResult) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    payload = {
        "risk": result.risk,
        "exit_code": result.exit_code,
        "pr_allowed": result.pr_allowed,
        "waiting_human": result.waiting_human,
        "reason": result.reason,
        "bundle": str(result.bundle) if result.bundle else "",
        "checks": [
            {"name": item.name, "stage": item.stage, "status": item.status, "detail": item.detail}
            for item in result.checks
        ],
    }
    (dest / "verify-result.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    logs = []
    for item in result.checks:
        if item.detail or item.log:
            logs.append(f"## {item.stage} {item.name} {item.status}\n{item.detail}\n{item.log}")
    (dest / "verify.log").write_text("\n".join(logs) + "\n", encoding="utf-8")


def _write_bundle(
    dest: Path,
    result: PipelineResult,
    inp: VerifyInput,
    security: dict,
    health_text: str,
    intents: list[dict],
) -> Path:
    bundle = dest / "verify-bundle"
    log_dir = bundle / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    for item in result.checks:
        if item.log or item.kind == "command":
            (log_dir / f"{item.name}.log").write_text((item.log or item.detail or "") + "\n", encoding="utf-8")
    if health_text:
        (bundle / "health.txt").write_text(health_text, encoding="utf-8")
    if security:
        (bundle / "security.json").write_text(json.dumps(security, indent=2) + "\n", encoding="utf-8")
    if intents:
        lines = ["# Smells outside this ticket", ""]
        for item in intents:
            lines.append(f"- {item.get('path')}: {item.get('kind')}")
        (dest / "intents-smells.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    if should_diagrams(result.risk, inp.changed_lines, inp.tiny_max_lines):
        diag = bundle / "diagrams"
        diag.mkdir(parents=True, exist_ok=True)
        changed = "\n".join(f"- {path}" for path in inp.changed) or "- none"
        (diag / "state.md").write_text("# State\n\n```mermaid\nstateDiagram-v2\n    [*] --> Changed\n```\n\n" + changed + "\n", encoding="utf-8")
        ui = [path for path in inp.changed if is_ui(path)]
        interaction = "# User interaction\n\n" + ("\n".join(f"- {path}" for path in ui) if ui else "no UI surface in this diff") + "\n"
        (diag / "user-interaction.md").write_text(interaction, encoding="utf-8")
        (diag / "feature-map.md").write_text("# Feature map\n\n" + (changed if ui else "no user-facing surface in this diff\n"), encoding="utf-8")
        tops = {Path(path).parts[0] for path in inp.changed if len(Path(path).parts) > 1}
        if len(tops) > 1:
            (diag / "architecture.md").write_text(
                "# Architecture sketch\n\nCrosses " + ", ".join(sorted(tops)) + ".\n",
                encoding="utf-8",
            )
    manifest = {
        "risk": result.risk,
        "pr_allowed": result.pr_allowed,
        "reason": result.reason,
        "checks": [{"name": item.name, "stage": item.stage, "status": item.status} for item in result.checks],
    }
    (bundle / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return bundle


def _finish(
    dest: Path,
    risk: str,
    checks: list[Check],
    *,
    code: int,
    allowed: bool,
    reason: str,
    waiting: bool = False,
    bundle: Path | None = None,
) -> PipelineResult:
    result = PipelineResult(
        risk=risk,
        checks=checks,
        exit_code=code,
        pr_allowed=allowed,
        reason=reason,
        bundle=bundle,
        waiting_human=waiting,
    )
    _write_result(dest, result)
    return result


def run_pipeline(
    repo: Path,
    inp: VerifyInput,
    dest: Path,
    runner=None,
    health=None,
    timeout: int = 1800,
) -> PipelineResult:
    from verify_infer import check_health, run_cmd

    risk = resolve_risk(inp)
    checks = plan_gates(repo, inp)
    run_cmd_fn = runner or (lambda path, cmd, timeout=None: run_cmd(path, cmd, timeout=timeout))
    health_fn = health or check_health
    health_text = ""
    security: dict = {}
    intents: list[dict] = []

    def run_static(check: Check) -> None:
        if check.kind == "command":
            _run_cmd(check, repo, run_cmd_fn, timeout)
            return
        _apply_builtin(check, repo, inp, risk)

    stage_a = [item for item in checks if item.stage == "A"]
    if stage_a:
        with ThreadPoolExecutor(max_workers=max(1, len(stage_a))) as pool:
            futures = [pool.submit(run_static, item) for item in stage_a]
            for future in futures:
                future.result()
    if _failed(checks):
        return _finish(dest, risk, checks, code=1, allowed=False, reason="static gate failed")

    for check in _ordered(checks, "B", B_ORDER):
        _run_cmd(check, repo, run_cmd_fn, timeout)
        if check.name == "coverage":
            _coverage_gate(check, inp)
        elif check.name == "pit":
            _pit_gate(check, inp)
        if check.required and check.status == "fail":
            return _finish(dest, risk, checks, code=1, allowed=False, reason=check.detail or f"{check.name} failed")

    for check in _ordered(checks, "C", C_ORDER):
        if check.name == "smoke":
            parts: list[str] = []
            url = (inp.commands or {}).get("health") or ""
            if url.startswith("http"):
                ok, msg = health_fn(url)
                parts.append(msg)
                health_text = msg + "\n"
                if not ok:
                    check.status = "fail"
                    check.detail = msg
                    check.log = "\n".join(parts)
                    return _finish(dest, risk, checks, code=1, allowed=False, reason=msg)
            if check.command and not check.command.startswith("http"):
                _run_cmd(check, repo, run_cmd_fn, timeout)
                parts.append(check.log)
            if check.status != "fail":
                check.status = "pass"
                check.detail = "smoke with boot check"
            check.log = "\n".join(parts) or check.log
        else:
            _run_cmd(check, repo, run_cmd_fn, timeout)
        if check.required and check.status == "fail":
            return _finish(dest, risk, checks, code=1, allowed=False, reason=check.detail or f"{check.name} failed")

    for check in checks:
        if check.stage != "D":
            continue
        if check.command:
            _run_cmd(check, repo, run_cmd_fn, timeout)
        security = _security_gate(check, repo, inp)
        if check.required and check.status == "fail":
            return _finish(dest, risk, checks, code=1, allowed=False, reason=check.detail or "security gate failed")

    smell = next((item for item in checks if item.name == "smells"), None)
    if smell is not None:
        findings = _find_smells(repo)
        fixes, intents = smell_actions(findings, set(inp.changed), risk, inp.fix_cap)
        originals: dict[Path, str] = {}
        for fix in fixes:
            path = repo / str(fix["path"])
            originals[path] = _read(path)
            path.write_text(_strip_trailing(originals[path]), encoding="utf-8")
        if fixes:
            saved = [(check, check.status, check.detail, check.log, check.exit_code) for check in checks]
            rerun_failed = False
            for check in checks:
                if check.kind != "command" or check.status != "pass":
                    continue
                if check.name == "smoke" or check.command.startswith("http"):
                    continue
                _run_cmd(check, repo, run_cmd_fn, timeout)
                if check.name == "coverage":
                    _coverage_gate(check, inp)
                elif check.name == "pit":
                    _pit_gate(check, inp)
                elif check.name == "security":
                    security = _security_gate(check, repo, inp)
                if check.status == "fail":
                    rerun_failed = True
                    break
            if rerun_failed:
                for path, text in originals.items():
                    path.write_text(text, encoding="utf-8")
                for check, status, detail, log, code in saved:
                    check.status, check.detail, check.log, check.exit_code = status, detail, log, code
                smell.detail = "smell fix reverted; earlier gates went red"
            else:
                smell.detail = f"fixed {len(fixes)} in-diff smell(s)"
        else:
            smell.detail = f"flagged {len(findings)}; intents {len(intents)}"
        smell.status = "pass"

    name = human_name(inp.human_text) if risk == "sensitive" else None
    if risk == "sensitive" and not name:
        result = _finish(
            dest,
            risk,
            checks,
            code=3,
            allowed=False,
            reason="waiting for named human",
            waiting=True,
        )
        result.bundle = _write_bundle(dest, result, inp, security, health_text, intents)
        _write_result(dest, result)
        return result

    reason = f"named human {name}" if name else "gates passed"
    result = _finish(dest, risk, checks, code=0, allowed=True, reason=reason)
    result.bundle = _write_bundle(dest, result, inp, security, health_text, intents)
    _write_result(dest, result)
    return result


def verify_input_from_config(
    cfg,
    repo: Path,
    *,
    changed: list[str] | tuple[str, ...] = (),
    changed_lines: int = 0,
    spec: str = "",
    labels: list[str] | tuple[str, ...] = (),
    explicit_risk: str = "",
    human_text: str = "",
    dep_diff: str = "",
) -> VerifyInput:
    from verify_infer import infer_recipe

    verification = cfg.verification
    commands = {str(key): str(value) for key, value in (verification.commands or {}).items() if str(value).strip()}
    override = (cfg.verify or {}).get(repo.name) or {}
    if not commands.get("unit") and override.get("test"):
        commands["unit"] = str(override["test"])
    if not commands.get("unit"):
        recipe = infer_recipe(repo, cfg)
        if recipe is not None:
            commands["unit"] = " ".join(recipe.test)
    if not commands.get("health"):
        health = (cfg.health or {}).get(repo.name) or override.get("health") or ""
        if health:
            commands["health"] = str(health)
    return VerifyInput(
        risk_class=verification.risk_class,
        explicit_risk=explicit_risk,
        labels=tuple(str(item) for item in labels),
        changed=tuple(changed),
        changed_lines=changed_lines,
        spec=spec,
        human_text=human_text,
        fix_cap=int(verification.fix_cap),
        tiny_max_lines=int(verification.tiny_max_lines),
        coverage_min_pct=float(verification.coverage_min_pct),
        pit_min_pct=float(verification.pit_min_pct),
        commands=commands,
        hot_paths=tuple(verification.hot_paths),
        protected_paths=tuple(verification.protected_paths),
        fail_closed=bool(cfg.verify_fail_closed),
        dep_diff=dep_diff,
    )


def run_for_config(repo: Path, cfg, dest: Path, changed: list[str] | None = None, spec: str = "", human_text: str = "", explicit_risk: str = "", labels: list[str] | None = None) -> PipelineResult:
    files = list(changed or [])
    line_count = 0
    for rel in files:
        line_count += len(_read(repo / rel).splitlines())
    inp = verify_input_from_config(
        cfg,
        repo,
        changed=files,
        changed_lines=line_count,
        spec=spec,
        labels=labels or [],
        explicit_risk=explicit_risk,
        human_text=human_text,
    )
    return run_pipeline(repo, inp, dest, timeout=int(getattr(cfg, "verify_timeout_sec", 1800) or 1800))
