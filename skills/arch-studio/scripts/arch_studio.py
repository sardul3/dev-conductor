#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from archstudio import __version__
from archstudio.builder import BuildBlocked, build_bundle
from archstudio.drawio import load_icons
from archstudio.model import all_findings, finding_summary, load_model
from archstudio.reports import diff_markdown, semantic_diff
from archstudio.server import ReviewServer


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="arch_studio.py", description="Compile governed architecture and UI specifications into draw.io and an interactive review workspace.")
    parser.add_argument("--version", action="version", version=f"arch-studio {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("doctor", help="Verify the skill package and local runtime.")

    validate = sub.add_parser("validate", help="Validate structure, architecture/UI quality, Azure governance, and Kubernetes readiness.")
    validate.add_argument("model")
    validate.add_argument("--json", action="store_true", dest="as_json")

    build = sub.add_parser("build", help="Generate the complete review bundle.")
    build.add_argument("model")
    build.add_argument("--out", required=True)
    build.add_argument("--strict", action="store_true", help="Write nothing unless all unwaived blockers are resolved.")
    build.add_argument("--json", action="store_true", dest="as_json")

    serve = sub.add_parser("serve", help="Serve the review workspace on loopback with optional Claude session bridge.")
    serve.add_argument("model")
    serve.add_argument("--out", required=True)
    serve.add_argument("--port", type=int, default=0)
    serve.add_argument("--open", action="store_true", dest="open_browser")
    serve.add_argument("--claude-bridge", action="store_true")
    serve.add_argument("--claude-session")
    serve.add_argument("--timeout", type=int, default=180)
    serve.add_argument("--max-budget-usd", type=float, default=1.0)

    diff = sub.add_parser("diff", help="Compare two canonical models semantically.")
    diff.add_argument("before")
    diff.add_argument("after")
    diff.add_argument("--out", required=True)
    return parser


def _print_findings(findings, as_json: bool) -> None:
    summary = finding_summary(findings)
    if as_json:
        print(json.dumps({"summary": summary, "findings": [item.to_dict() for item in findings]}, indent=2, ensure_ascii=False))
        return
    print(f"Gate: {summary['status'].upper()} · blocking={summary['blocking']} waived={summary['waived']} warnings={summary['warnings']}")
    if not findings:
        print("No findings.")
        return
    order = {"blocker": 0, "warning": 1, "info": 2}
    for item in sorted(findings, key=lambda value: (order.get(value.level, 9), value.gate, value.code, value.subject)):
        waiver = f" [waived: {item.waived_by}]" if item.waived_by else ""
        print(f"{item.level.upper():7} {item.code:30} {item.subject}{waiver}")
        print(f"         {item.message}")
        print(f"         Fix: {item.remediation}")


def doctor() -> int:
    checks = []
    checks.append((sys.version_info >= (3, 10), f"Python {sys.version.split()[0]} (requires 3.10+)"))
    for relative in ("SKILL.md", "assets/architecture.schema.json", "assets/azure-icons.json", "references/ui-specification.md", "evals/evals.json"):
        path = SKILL_ROOT / relative
        checks.append((path.is_file(), f"{relative} present"))
    try:
        json.loads((SKILL_ROOT / "assets" / "architecture.schema.json").read_text(encoding="utf-8"))
        evals = json.loads((SKILL_ROOT / "evals" / "evals.json").read_text(encoding="utf-8"))
        if evals.get("skill_name") != "arch-studio" or not evals.get("evals"):
            raise ValueError("Anthropic eval set is empty or targets another skill")
        load_icons(SKILL_ROOT / "assets" / "azure-icons.json")
        checks.append((True, "Architecture/UI schema, Azure icons, and Anthropic eval set parse"))
    except Exception as exc:
        checks.append((False, f"Asset parse failed: {exc}"))
    checks.append((shutil.which("claude") is not None, "claude CLI available (optional; required only for review chat bridge)"))
    required_failed = False
    for ok, label in checks:
        optional = "optional" in label
        print(f"{'OK' if ok else 'WARN' if optional else 'FAIL'}  {label}")
        if not ok and not optional:
            required_failed = True
    return 1 if required_failed else 0


def main() -> int:
    args = _parser().parse_args()
    if args.command == "doctor":
        return doctor()
    if args.command == "validate":
        model = load_model(args.model)
        icons = load_icons(SKILL_ROOT / "assets" / "azure-icons.json")
        findings = all_findings(model, set(icons))
        _print_findings(findings, args.as_json)
        return 1 if finding_summary(findings)["status"] == "fail" else 0
    if args.command == "build":
        model = load_model(args.model)
        try:
            result = build_bundle(model, args.out, SKILL_ROOT, strict=args.strict, generator_version=__version__)
        except BuildBlocked as exc:
            _print_findings(exc.findings, args.as_json)
            if not args.as_json:
                print(str(exc), file=sys.stderr)
            return 1
        if args.as_json:
            print(json.dumps({"status": "ok", "project_id": result.project_id, "model_sha256": result.model_sha256, "gate": result.summary, "files": [str(path) for path in result.files]}, indent=2))
        else:
            print(f"Built {result.project_id} · gate={result.summary['status']} · {len(result.files)} files")
            for path in result.files:
                print(path)
        return 0
    if args.command == "serve":
        model_path = Path(args.model).resolve()
        server = ReviewServer(
            model_path=model_path,
            output_directory=Path(args.out),
            skill_root=SKILL_ROOT,
            generator_version=__version__,
            port=args.port,
            claude_bridge=args.claude_bridge,
            claude_session=args.claude_session,
            timeout=args.timeout,
            max_budget_usd=args.max_budget_usd,
        )
        server.start(open_browser=args.open_browser)
        return 0
    if args.command == "diff":
        before = load_model(args.before)
        after = load_model(args.after)
        delta = semantic_diff(before, after)
        output = Path(args.out)
        output.parent.mkdir(parents=True, exist_ok=True)
        if output.suffix.lower() == ".json":
            output.write_text(json.dumps(delta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        else:
            output.write_bytes(diff_markdown(delta))
        print(output.resolve())
        return 0
    return 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(2)
