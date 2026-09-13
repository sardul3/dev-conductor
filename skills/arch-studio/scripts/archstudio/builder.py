from __future__ import annotations

import json
import os
import shutil
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .drawio import load_icons, render_drawio
from .model import Finding, all_findings, finding_summary, model_digest, pretty_json_bytes, sha256_file
from .reports import (
    decisions_markdown,
    design_tokens_json,
    governance_json,
    governance_markdown,
    receipt_payload,
    risk_threat_markdown,
    traceability_csv,
    ui_acceptance_markdown,
    ui_component_matrix_csv,
    ui_specification_markdown,
)
from .review import render_review_html


@dataclass
class BuildResult:
    project_id: str
    output_directory: Path
    files: list[Path]
    findings: list[Finding]
    summary: dict[str, Any]
    model_sha256: str


class BuildBlocked(RuntimeError):
    def __init__(self, message: str, findings: list[Finding]):
        super().__init__(message)
        self.findings = findings


def build_bundle(
    model: dict[str, Any],
    output_directory: str | Path,
    skill_root: str | Path,
    *,
    strict: bool,
    generator_version: str,
) -> BuildResult:
    root = Path(skill_root)
    out = Path(output_directory).resolve()
    icons = load_icons(root / "assets" / "azure-icons.json")
    findings = all_findings(model, set(icons))
    summary = finding_summary(findings)
    structural = [item for item in findings if item.blocking and item.gate == "structure"]
    if structural:
        raise BuildBlocked("structural validation failed; no artifacts were written", findings)
    if strict and summary["status"] != "pass":
        raise BuildBlocked("strict architecture gate failed; no artifacts were written", findings)

    project_id = str(model.get("project", {}).get("id", "architecture"))
    drawio_name = f"{project_id}.drawio"
    model_name = f"{project_id}.arch.json"
    rendered_findings = [item.to_dict() for item in findings]
    payloads: dict[str, bytes] = {
        model_name: pretty_json_bytes(model),
        drawio_name: render_drawio(model, icons, generator_version),
        "review.html": render_review_html(model, rendered_findings, model_digest(model), generator_version),
        "governance-report.json": governance_json(model, findings),
        "governance-report.md": governance_markdown(model, findings),
        "traceability.csv": traceability_csv(model),
        "architecture-decisions.md": decisions_markdown(model),
        "risk-and-threat-summary.md": risk_threat_markdown(model),
    }
    ui_active = isinstance(model.get("ui_spec"), dict) and model["ui_spec"].get("status") != "not-requested"
    if ui_active:
        payloads.update(
            {
                "ui-specification.md": ui_specification_markdown(model),
                "ui-component-matrix.csv": ui_component_matrix_csv(model),
                "ui-acceptance-plan.md": ui_acceptance_markdown(model),
                "design-tokens.json": design_tokens_json(model),
            }
        )
    _verify_payloads(payloads, project_id, len(model.get("views", [])), ui_active)

    out.mkdir(parents=True, exist_ok=True)
    candidate_dir = Path(tempfile.mkdtemp(prefix=f".{project_id}-candidate-", dir=out))
    try:
        for name, content in payloads.items():
            candidate = candidate_dir / name
            candidate.write_bytes(content)
            with candidate.open("rb") as handle:
                os.fsync(handle.fileno())
        artifacts = []
        for name in payloads:
            candidate = candidate_dir / name
            artifacts.append({"name": name, "sha256": sha256_file(candidate), "bytes": candidate.stat().st_size})
        receipt = receipt_payload(model, artifacts, summary, generator_version)
        receipt_path = candidate_dir / "build-receipt.json"
        receipt_path.write_bytes(receipt)
        with receipt_path.open("rb") as handle:
            os.fsync(handle.fileno())
        committed: list[Path] = []
        for name in [*payloads, "build-receipt.json"]:
            target = out / name
            os.replace(candidate_dir / name, target)
            committed.append(target)
    finally:
        shutil.rmtree(candidate_dir, ignore_errors=True)

    return BuildResult(
        project_id=project_id,
        output_directory=out,
        files=committed,
        findings=findings,
        summary=summary,
        model_sha256=model_digest(model),
    )


def _verify_payloads(payloads: dict[str, bytes], project_id: str, expected_pages: int, ui_active: bool) -> None:
    drawio = payloads[f"{project_id}.drawio"]
    root = ET.fromstring(drawio)
    diagrams = root.findall("diagram")
    if len(diagrams) != expected_pages:
        raise ValueError(f"draw.io page count mismatch: expected {expected_pages}, generated {len(diagrams)}")
    for diagram in diagrams:
        if diagram.find("mxGraphModel/root") is None:
            raise ValueError(f"draw.io page '{diagram.get('name')}' has no mxGraphModel root")
    review = payloads["review.html"].decode("utf-8")
    required = ("id=\"arch-model\"", "class=\"architecture-svg\"", "Export review JSON", "Copy change prompt")
    for token in required:
        if token not in review:
            raise ValueError(f"review HTML is missing required marker: {token}")
    forbidden = ("@keyframes", "animation:", "<canvas", 'src="http', 'href="http')
    for token in forbidden:
        if token in review:
            raise ValueError(f"review HTML violates static self-contained contract: {token}")
    json.loads(payloads["governance-report.json"])
    if ui_active:
        for name in ("ui-specification.md", "ui-component-matrix.csv", "ui-acceptance-plan.md", "design-tokens.json"):
            if not payloads.get(name):
                raise ValueError(f"active UI specification is missing artifact: {name}")
        json.loads(payloads["design-tokens.json"])
        if "ui-screen:" not in review or "ui-state:" not in review:
            raise ValueError("interactive review does not index UI screens and states")
