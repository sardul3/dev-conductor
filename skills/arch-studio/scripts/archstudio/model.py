from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import tempfile
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable


ID_RE = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
TOP_LEVEL_REQUIRED = (
    "schema_version",
    "project",
    "requirements",
    "platform",
    "controls",
    "components",
    "relationships",
    "views",
    "decisions",
    "risks",
    "assumptions",
    "open_questions",
    "waivers",
)
COLLECTIONS_WITH_IDS = (
    "requirements",
    "controls",
    "components",
    "relationships",
    "views",
    "decisions",
    "risks",
    "assumptions",
    "open_questions",
    "waivers",
)
VIEW_TYPES = {
    "system-context",
    "container",
    "component",
    "deployment",
    "network",
    "security",
    "data-flow",
    "sequence",
    "kubernetes",
    "ci-cd",
    "observability",
    "resilience",
    "migration",
    "lifecycle",
    "executive",
    "user-flow",
    "ui-wireframe",
    "ui-state-map",
    "generic",
}
UI_VIEW_TYPES = {"user-flow", "ui-wireframe", "ui-state-map"}
UI_REQUIRED_STATES = {"default"}
UI_DATA_STATES = {"loading", "empty", "error"}
COMPONENT_KINDS = {
    "actor",
    "external-system",
    "client",
    "gateway",
    "service",
    "function",
    "worker",
    "message-broker",
    "database",
    "cache",
    "storage",
    "identity",
    "security",
    "observability",
    "pipeline",
    "repository",
    "kubernetes",
    "network",
    "generic",
}
DATA_STORES = {"database", "cache", "storage"}
SENSITIVE = {"confidential", "restricted"}


@dataclass
class Finding:
    code: str
    level: str
    gate: str
    subject: str
    message: str
    remediation: str
    waiver_allowed: bool = True
    waived_by: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def blocking(self) -> bool:
        return self.level == "blocker" and not self.waived_by


def load_model(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    try:
        data = json.loads(source.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"architecture model not found: {source}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"invalid JSON in {source}: line {exc.lineno}, column {exc.colno}: {exc.msg}"
        ) from exc
    if not isinstance(data, dict):
        raise ValueError("architecture model must be a JSON object")
    return data


def canonical_json_bytes(model: dict[str, Any]) -> bytes:
    return (json.dumps(model, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")


def pretty_json_bytes(model: dict[str, Any]) -> bytes:
    return (json.dumps(model, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def model_digest(model: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json_bytes(model)).hexdigest()


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_write(path: str | Path, content: bytes) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=target.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, target)
    except Exception:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise


def dig(value: Any, *path: str, default: Any = None) -> Any:
    current = value
    for key in path:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current


def _finding(
    findings: list[Finding],
    code: str,
    level: str,
    gate: str,
    subject: str,
    message: str,
    remediation: str,
    waiver_allowed: bool = True,
) -> None:
    findings.append(
        Finding(
            code=code,
            level=level,
            gate=gate,
            subject=subject,
            message=message,
            remediation=remediation,
            waiver_allowed=waiver_allowed,
        )
    )


def _is_nonempty(value: Any) -> bool:
    return value is not None and value != "" and value != [] and value != {}


def _is_date(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        date.fromisoformat(value[:10])
        return True
    except ValueError:
        return False


def _valid_id(value: Any) -> bool:
    return isinstance(value, str) and bool(ID_RE.fullmatch(value))


def _rect_overlap(a: dict[str, Any], b: dict[str, Any], padding: float = 8.0) -> bool:
    try:
        return not (
            a["x"] + a["w"] + padding <= b["x"]
            or b["x"] + b["w"] + padding <= a["x"]
            or a["y"] + a["h"] + padding <= b["y"]
            or b["y"] + b["h"] + padding <= a["y"]
        )
    except (KeyError, TypeError):
        return False


def _inside(child: dict[str, Any], parent: dict[str, Any], padding: float = 20.0) -> bool:
    try:
        return (
            child["x"] >= parent["x"] + padding
            and child["y"] >= parent["y"] + padding
            and child["x"] + child["w"] <= parent["x"] + parent["w"] - padding
            and child["y"] + child["h"] <= parent["y"] + parent["h"] - padding
        )
    except (KeyError, TypeError):
        return False


def _validate_evidence(findings: list[Finding], subject: str, evidence: Any) -> None:
    if not isinstance(evidence, list):
        _finding(
            findings,
            "STRUCT-EVIDENCE-TYPE",
            "blocker",
            "structure",
            subject,
            "Evidence must be an array.",
            "Use an empty array or evidence objects with source, confidence, and note.",
            False,
        )
        return
    for index, item in enumerate(evidence):
        item_subject = f"{subject}.evidence[{index}]"
        if not isinstance(item, dict):
            _finding(findings, "STRUCT-EVIDENCE-OBJECT", "blocker", "structure", item_subject, "Evidence entry must be an object.", "Replace it with a valid evidence object.", False)
            continue
        if item.get("source") not in {"repository", "document", "user", "runtime", "inference", "proposal"}:
            _finding(findings, "STRUCT-EVIDENCE-SOURCE", "blocker", "structure", item_subject, "Evidence source is missing or unsupported.", "Choose repository, document, user, runtime, inference, or proposal.", False)
        if item.get("confidence") not in {"high", "medium", "low"}:
            _finding(findings, "STRUCT-EVIDENCE-CONFIDENCE", "blocker", "structure", item_subject, "Evidence confidence is missing or unsupported.", "Choose high, medium, or low.", False)
        if not _is_nonempty(item.get("note")):
            _finding(findings, "STRUCT-EVIDENCE-NOTE", "blocker", "structure", item_subject, "Evidence must state what it supports.", "Add a concise evidence note.", False)
        if item.get("source") in {"repository", "document", "runtime"} and not _is_nonempty(item.get("reference")):
            _finding(findings, "EVIDENCE-REFERENCE", "warning", "quality", item_subject, "Observed evidence has no reference.", "Add a relative path, document identifier, or scoped runtime reference.")


def validate_structure(model: dict[str, Any], icon_ids: set[str] | None = None) -> list[Finding]:
    findings: list[Finding] = []

    for key in TOP_LEVEL_REQUIRED:
        if key not in model:
            _finding(findings, "STRUCT-TOP-REQUIRED", "blocker", "structure", key, f"Missing top-level field '{key}'.", f"Add '{key}' using the canonical schema.", False)
    if findings:
        return findings

    if model.get("schema_version") != "1.0":
        _finding(findings, "STRUCT-SCHEMA-VERSION", "blocker", "structure", "schema_version", "Only schema_version 1.0 is supported.", "Set schema_version to 1.0 and migrate fields to the bundled schema.", False)

    project = model.get("project")
    if not isinstance(project, dict):
        _finding(findings, "STRUCT-PROJECT", "blocker", "structure", "project", "Project must be an object.", "Create a project object using the schema.", False)
        project = {}
    for key in ("id", "title", "version", "status", "description", "cloud_provider", "environments", "primary_region", "owners", "data_residency", "classification", "reviewed_at"):
        if not _is_nonempty(project.get(key)) and key != "secondary_region":
            _finding(findings, "STRUCT-PROJECT-FIELD", "blocker", "structure", f"project.{key}", f"Project field '{key}' is required.", "Supply an explicit value; use an assumption rather than inventing a fact.", False)
    if project.get("id") and not _valid_id(project.get("id")):
        _finding(findings, "STRUCT-ID-FORMAT", "blocker", "structure", "project.id", "Project ID must use lowercase kebab case.", "Use an ID such as retail-order-integration.", False)
    if project.get("status") not in {"draft", "in-review", "approved", "implemented", "retired"}:
        _finding(findings, "STRUCT-PROJECT-STATUS", "blocker", "structure", "project.status", "Unsupported project status.", "Choose draft, in-review, approved, implemented, or retired.", False)
    if project.get("reviewed_at") and not _is_date(project.get("reviewed_at")):
        _finding(findings, "STRUCT-DATE", "blocker", "structure", "project.reviewed_at", "reviewed_at is not an ISO date.", "Use YYYY-MM-DD.", False)

    for name in COLLECTIONS_WITH_IDS:
        if not isinstance(model.get(name), list):
            _finding(findings, "STRUCT-COLLECTION", "blocker", "structure", name, f"'{name}' must be an array.", "Use an empty array when no items apply.", False)

    if any(not isinstance(model.get(name), list) for name in COLLECTIONS_WITH_IDS):
        return findings

    global_ids: dict[str, str] = {}
    indexes: dict[str, dict[str, dict[str, Any]]] = {}
    for name in COLLECTIONS_WITH_IDS:
        indexes[name] = {}
        for index, item in enumerate(model[name]):
            subject = f"{name}[{index}]"
            if not isinstance(item, dict):
                _finding(findings, "STRUCT-ITEM-OBJECT", "blocker", "structure", subject, f"Every {name} item must be an object.", "Replace the item with a valid object.", False)
                continue
            entity_id = item.get("id")
            if not _valid_id(entity_id):
                _finding(findings, "STRUCT-ID-FORMAT", "blocker", "structure", f"{subject}.id", "ID must use lowercase kebab case and start with a letter.", "Use a stable ID such as order-api.", False)
                continue
            if entity_id in global_ids:
                _finding(findings, "STRUCT-ID-DUPLICATE", "blocker", "structure", f"{subject}.id", f"ID '{entity_id}' is already used by {global_ids[entity_id]}.", "Use a globally unique stable ID.", False)
            else:
                global_ids[entity_id] = f"{name}.{entity_id}"
            indexes[name][entity_id] = item

    requirements = indexes["requirements"]
    controls = indexes["controls"]
    components = indexes["components"]
    relationships = indexes["relationships"]
    decisions = indexes["decisions"]
    risks = indexes["risks"]

    for req_id, requirement in requirements.items():
        subject = f"requirements.{req_id}"
        for key in ("type", "text", "priority", "status", "owner", "acceptance", "evidence"):
            if key not in requirement or (key != "evidence" and not _is_nonempty(requirement.get(key))):
                _finding(findings, "STRUCT-REQUIREMENT-FIELD", "blocker", "structure", f"{subject}.{key}", f"Requirement field '{key}' is required.", "Complete the requirement or mark it explicitly unresolved.", False)
        _validate_evidence(findings, subject, requirement.get("evidence", []))

    for control_id, control in controls.items():
        subject = f"controls.{control_id}"
        for key in ("name", "domain", "description", "implementation", "owner", "status", "requirements", "risks", "evidence"):
            if key not in control or (key not in {"requirements", "risks", "evidence"} and not _is_nonempty(control.get(key))):
                _finding(findings, "STRUCT-CONTROL-FIELD", "blocker", "structure", f"{subject}.{key}", f"Control field '{key}' is required.", "Complete the control definition.", False)
        for ref in control.get("requirements", []):
            if ref not in requirements:
                _finding(findings, "STRUCT-REFERENCE", "blocker", "structure", subject, f"Unknown requirement reference '{ref}'.", "Reference an existing requirement ID.", False)
        for ref in control.get("risks", []):
            if ref not in risks:
                _finding(findings, "STRUCT-REFERENCE", "blocker", "structure", subject, f"Unknown risk reference '{ref}'.", "Reference an existing risk ID.", False)
        _validate_evidence(findings, subject, control.get("evidence", []))

    for component_id, component in components.items():
        subject = f"components.{component_id}"
        for key in ("name", "kind", "description", "technology", "owner", "criticality", "data_classification", "lifecycle", "public_exposure", "requirements", "controls", "evidence"):
            if key not in component or (key not in {"requirements", "controls", "evidence"} and not _is_nonempty(component.get(key))):
                _finding(findings, "STRUCT-COMPONENT-FIELD", "blocker", "structure", f"{subject}.{key}", f"Component field '{key}' is required.", "Complete the component metadata.", False)
        if component.get("kind") not in COMPONENT_KINDS:
            _finding(findings, "STRUCT-COMPONENT-KIND", "blocker", "structure", f"{subject}.kind", "Unsupported component kind.", "Use a kind defined in architecture.schema.json.", False)
        for ref in component.get("requirements", []):
            if ref not in requirements:
                _finding(findings, "STRUCT-REFERENCE", "blocker", "structure", subject, f"Unknown requirement reference '{ref}'.", "Reference an existing requirement ID.", False)
        for ref in component.get("controls", []):
            if ref not in controls:
                _finding(findings, "STRUCT-REFERENCE", "blocker", "structure", subject, f"Unknown control reference '{ref}'.", "Reference an existing control ID.", False)
        if icon_ids is not None and component.get("azure_service") and component["azure_service"] not in icon_ids:
            _finding(findings, "DRAWIO-AZURE-ICON", "warning", "quality", subject, f"Unknown Azure icon ID '{component['azure_service']}'.", "Use an ID from assets/azure-icons.json or omit azure_service for a generic symbol.")
        _validate_evidence(findings, subject, component.get("evidence", []))

    for relationship_id, relationship in relationships.items():
        subject = f"relationships.{relationship_id}"
        for key in ("from", "to", "label", "direction", "protocol", "port", "auth", "mode", "encrypted", "data", "failure_behavior", "requirements", "controls", "evidence"):
            if key not in relationship or (key not in {"port", "data", "requirements", "controls", "evidence"} and not _is_nonempty(relationship.get(key))):
                _finding(findings, "STRUCT-RELATIONSHIP-FIELD", "blocker", "structure", f"{subject}.{key}", f"Relationship field '{key}' is required.", "Complete the connection contract.", False)
        for endpoint in ("from", "to"):
            if relationship.get(endpoint) not in components:
                _finding(findings, "STRUCT-RELATIONSHIP-ENDPOINT", "blocker", "structure", f"{subject}.{endpoint}", f"Unknown component '{relationship.get(endpoint)}'.", "Reference an existing component ID.", False)
        if len(str(relationship.get("label", "")).strip()) < 3:
            _finding(findings, "DIAGRAM-EDGE-LABEL", "blocker", "quality", subject, "Connection label is missing or vague.", "State the action or data plus protocol/auth/mode when known.")
        for ref in relationship.get("requirements", []):
            if ref not in requirements:
                _finding(findings, "STRUCT-REFERENCE", "blocker", "structure", subject, f"Unknown requirement reference '{ref}'.", "Reference an existing requirement ID.", False)
        for ref in relationship.get("controls", []):
            if ref not in controls:
                _finding(findings, "STRUCT-REFERENCE", "blocker", "structure", subject, f"Unknown control reference '{ref}'.", "Reference an existing control ID.", False)
        _validate_evidence(findings, subject, relationship.get("evidence", []))

    for view_id, view in indexes["views"].items():
        _validate_view(findings, view_id, view, components, relationships, requirements, decisions)

    ui_ids = _validate_ui_spec(findings, model.get("ui_spec"), indexes["views"], components, relationships, requirements, set(global_ids))
    referencable = set(global_ids) | ui_ids
    for decision_id, decision in decisions.items():
        subject = f"decisions.{decision_id}"
        for key in ("title", "status", "context", "choice", "rationale", "alternatives", "consequences", "owner", "date", "affected"):
            if key not in decision:
                _finding(findings, "STRUCT-DECISION-FIELD", "blocker", "structure", f"{subject}.{key}", f"Decision field '{key}' is required.", "Complete the ADR.", False)
        for ref in decision.get("affected", []):
            if ref not in referencable:
                _finding(findings, "STRUCT-REFERENCE", "blocker", "structure", subject, f"Unknown affected ID '{ref}'.", "Reference an existing model entity ID.", False)

    for risk_id, risk in risks.items():
        subject = f"risks.{risk_id}"
        for key in ("title", "category", "likelihood", "impact", "exposure", "mitigation", "owner", "status", "affected"):
            if key not in risk or (key != "affected" and not _is_nonempty(risk.get(key))):
                _finding(findings, "STRUCT-RISK-FIELD", "blocker", "structure", f"{subject}.{key}", f"Risk field '{key}' is required.", "Complete the risk entry.", False)
        for ref in risk.get("affected", []):
            if ref not in referencable:
                _finding(findings, "STRUCT-REFERENCE", "blocker", "structure", subject, f"Unknown affected ID '{ref}'.", "Reference an existing model entity ID.", False)

    for assumption_id, assumption in indexes["assumptions"].items():
        subject = f"assumptions.{assumption_id}"
        for key in ("text", "consequence", "owner", "revisit_by", "status"):
            if not _is_nonempty(assumption.get(key)):
                _finding(findings, "STRUCT-ASSUMPTION-FIELD", "blocker", "structure", f"{subject}.{key}", f"Assumption field '{key}' is required.", "Complete the assumption and its review date.", False)
        if assumption.get("revisit_by") and not _is_date(assumption.get("revisit_by")):
            _finding(findings, "STRUCT-DATE", "blocker", "structure", f"{subject}.revisit_by", "Assumption revisit date is invalid.", "Use YYYY-MM-DD.", False)

    for question_id, question in indexes["open_questions"].items():
        subject = f"open_questions.{question_id}"
        for key in ("question", "owner", "blocking", "due", "consequence", "status"):
            if key not in question or (key != "blocking" and not _is_nonempty(question.get(key))):
                _finding(findings, "STRUCT-QUESTION-FIELD", "blocker", "structure", f"{subject}.{key}", f"Open-question field '{key}' is required.", "Complete the question metadata.", False)

    _validate_waiver_shape(findings, indexes["waivers"])
    return findings


def _validate_view(
    findings: list[Finding],
    view_id: str,
    view: dict[str, Any],
    components: dict[str, dict[str, Any]],
    relationships: dict[str, dict[str, Any]],
    requirements: dict[str, dict[str, Any]],
    decisions: dict[str, dict[str, Any]],
) -> None:
    subject = f"views.{view_id}"
    for key in ("title", "type", "purpose", "width", "height", "nodes", "legend", "requirements", "decisions"):
        if key not in view:
            _finding(findings, "STRUCT-VIEW-FIELD", "blocker", "structure", f"{subject}.{key}", f"View field '{key}' is required.", "Complete the view definition.", False)
    if view.get("type") not in VIEW_TYPES:
        _finding(findings, "STRUCT-VIEW-TYPE", "blocker", "structure", f"{subject}.type", "Unsupported view type.", "Use a type from architecture.schema.json.", False)
    if not isinstance(view.get("width"), (int, float)) or view.get("width", 0) < 640 or not isinstance(view.get("height"), (int, float)) or view.get("height", 0) < 480:
        _finding(findings, "STRUCT-VIEW-SIZE", "blocker", "structure", subject, "View must be at least 640 by 480.", "Increase width and height.", False)

    legend = view.get("legend")
    if not isinstance(legend, dict) or legend.get("mode") not in {"auto", "authored", "hidden"}:
        _finding(findings, "STRUCT-LEGEND", "blocker", "structure", f"{subject}.legend", "Legend mode must be auto, authored, or hidden.", "Use auto unless project-specific notation needs authored entries.", False)
    elif legend.get("mode") == "hidden":
        _finding(findings, "DIAGRAM-LEGEND-HIDDEN", "warning", "quality", subject, "View legend is hidden.", "Use an automatic or authored legend unless the user explicitly accepted no legend.")

    boundaries = view.get("boundaries", [])
    if not isinstance(boundaries, list):
        _finding(findings, "STRUCT-BOUNDARIES", "blocker", "structure", f"{subject}.boundaries", "Boundaries must be an array.", "Use an empty array when none apply.", False)
        boundaries = []
    boundary_index: dict[str, dict[str, Any]] = {}
    for index, boundary in enumerate(boundaries):
        b_subject = f"{subject}.boundaries[{index}]"
        if not isinstance(boundary, dict) or not _valid_id(boundary.get("id")):
            _finding(findings, "STRUCT-BOUNDARY-ID", "blocker", "structure", b_subject, "Boundary needs a lowercase kebab-case ID.", "Add a stable boundary ID.", False)
            continue
        if boundary["id"] in boundary_index:
            _finding(findings, "STRUCT-BOUNDARY-DUPLICATE", "blocker", "structure", b_subject, f"Duplicate boundary ID '{boundary['id']}'.", "Use a unique ID within the view.", False)
        boundary_index[boundary["id"]] = boundary
        for key in ("label", "kind", "x", "y", "w", "h"):
            if key not in boundary:
                _finding(findings, "STRUCT-BOUNDARY-FIELD", "blocker", "structure", f"{b_subject}.{key}", f"Boundary field '{key}' is required.", "Complete the boundary geometry.", False)

    for boundary_id, boundary in boundary_index.items():
        parent_id = boundary.get("parent")
        if parent_id:
            parent = boundary_index.get(parent_id)
            if not parent:
                _finding(findings, "STRUCT-BOUNDARY-PARENT", "blocker", "structure", f"{subject}.boundaries.{boundary_id}", f"Unknown parent boundary '{parent_id}'.", "Reference a boundary in the same view.", False)
            elif not _inside(boundary, parent, 8):
                _finding(findings, "DIAGRAM-BOUNDARY-CONTAINMENT", "blocker", "quality", f"{subject}.boundaries.{boundary_id}", f"Boundary '{boundary_id}' is not contained by '{parent_id}'.", "Move or resize the child boundary within its parent.")

    nodes = view.get("nodes", [])
    if not isinstance(nodes, list):
        _finding(findings, "STRUCT-NODES", "blocker", "structure", f"{subject}.nodes", "Nodes must be an array.", "Use an empty array only for a sequence view with participants.", False)
        nodes = []
    placed: dict[str, dict[str, Any]] = {}
    for index, node in enumerate(nodes):
        n_subject = f"{subject}.nodes[{index}]"
        if not isinstance(node, dict):
            _finding(findings, "STRUCT-NODE-OBJECT", "blocker", "structure", n_subject, "Node placement must be an object.", "Create a valid node placement.", False)
            continue
        component_id = node.get("component")
        if component_id not in components:
            _finding(findings, "STRUCT-NODE-COMPONENT", "blocker", "structure", n_subject, f"Unknown component '{component_id}'.", "Reference an existing component.", False)
            continue
        if component_id in placed:
            _finding(findings, "STRUCT-NODE-DUPLICATE", "blocker", "structure", n_subject, f"Component '{component_id}' is placed twice in one view.", "Keep one placement per component per view.", False)
        placed[component_id] = node
        for key in ("x", "y", "w", "h"):
            if not isinstance(node.get(key), (int, float)):
                _finding(findings, "STRUCT-NODE-GEOMETRY", "blocker", "structure", f"{n_subject}.{key}", f"Node geometry '{key}' must be numeric.", "Supply explicit canvas coordinates.", False)
        boundary_id = node.get("boundary")
        if boundary_id:
            boundary = boundary_index.get(boundary_id)
            if not boundary:
                _finding(findings, "STRUCT-NODE-BOUNDARY", "blocker", "structure", n_subject, f"Unknown boundary '{boundary_id}'.", "Reference a boundary in the same view.", False)
            elif not _inside(node, boundary, 16):
                _finding(findings, "DIAGRAM-NODE-CONTAINMENT", "blocker", "quality", n_subject, f"Node '{component_id}' is not contained by '{boundary_id}'.", "Move or resize the node within the boundary.")

    node_values = list(placed.items())
    for i, (left_id, left) in enumerate(node_values):
        for right_id, right in node_values[i + 1 :]:
            if left.get("boundary") != right.get("boundary"):
                continue
            if _rect_overlap(left, right):
                _finding(findings, "DIAGRAM-NODE-OVERLAP", "blocker", "quality", subject, f"Nodes '{left_id}' and '{right_id}' overlap or have insufficient separation.", "Move the nodes at least 8 canvas units apart.")

    if view.get("type") == "sequence":
        participants = view.get("participants", [])
        if not isinstance(participants, list) or len(participants) < 2:
            _finding(findings, "SEQUENCE-PARTICIPANTS", "blocker", "quality", subject, "Sequence view needs at least two participants.", "Add ordered component IDs to participants.")
            participants = []
        for participant in participants:
            if participant not in components:
                _finding(findings, "STRUCT-SEQUENCE-PARTICIPANT", "blocker", "structure", subject, f"Unknown sequence participant '{participant}'.", "Reference an existing component ID.", False)
        interactions = view.get("interactions", [])
        if not isinstance(interactions, list) or not interactions:
            _finding(findings, "SEQUENCE-INTERACTIONS", "blocker", "quality", subject, "Sequence view needs ordered interactions.", "Add success and relevant failure-path interactions.")
            interactions = []
        seen_interactions: set[str] = set()
        for index, interaction in enumerate(interactions):
            i_subject = f"{subject}.interactions[{index}]"
            if not isinstance(interaction, dict) or not _valid_id(interaction.get("id")):
                _finding(findings, "STRUCT-INTERACTION-ID", "blocker", "structure", i_subject, "Interaction needs a lowercase kebab-case ID.", "Add a stable interaction ID.", False)
                continue
            if interaction["id"] in seen_interactions:
                _finding(findings, "STRUCT-INTERACTION-DUPLICATE", "blocker", "structure", i_subject, "Duplicate interaction ID.", "Use a unique interaction ID.", False)
            seen_interactions.add(interaction["id"])
            if interaction.get("from") not in participants or interaction.get("to") not in participants:
                _finding(findings, "STRUCT-INTERACTION-ENDPOINT", "blocker", "structure", i_subject, "Interaction endpoints must be listed participants.", "Add the component to participants or correct the endpoint.", False)
            if len(str(interaction.get("label", "")).strip()) < 2:
                _finding(findings, "SEQUENCE-LABEL", "blocker", "quality", i_subject, "Sequence interaction needs a meaningful label.", "State the action, event, response, or failure.")
    else:
        edge_ids = view.get("edges", [])
        if not isinstance(edge_ids, list):
            _finding(findings, "STRUCT-VIEW-EDGES", "blocker", "structure", f"{subject}.edges", "View edges must be an array.", "Use relationship IDs.", False)
            edge_ids = []
        for edge_id in edge_ids:
            relationship = relationships.get(edge_id)
            if not relationship:
                _finding(findings, "STRUCT-VIEW-EDGE", "blocker", "structure", subject, f"Unknown relationship '{edge_id}'.", "Reference an existing relationship ID.", False)
            elif relationship.get("from") not in placed or relationship.get("to") not in placed:
                _finding(findings, "DIAGRAM-EDGE-ENDPOINT", "blocker", "quality", subject, f"Relationship '{edge_id}' has an endpoint not placed in this view.", "Place both endpoint components or remove the edge from this view.")

    for ref in view.get("requirements", []):
        if ref not in requirements:
            _finding(findings, "STRUCT-REFERENCE", "blocker", "structure", subject, f"Unknown requirement reference '{ref}'.", "Reference an existing requirement ID.", False)
    for ref in view.get("decisions", []):
        if ref not in decisions:
            _finding(findings, "STRUCT-REFERENCE", "blocker", "structure", subject, f"Unknown decision reference '{ref}'.", "Reference an existing decision ID.", False)


def _validate_ui_spec(
    findings: list[Finding],
    ui_spec: Any,
    views: dict[str, dict[str, Any]],
    architecture_components: dict[str, dict[str, Any]],
    relationships: dict[str, dict[str, Any]],
    requirements: dict[str, dict[str, Any]],
    global_ids: set[str],
) -> set[str]:
    ui_views = {view_id: view for view_id, view in views.items() if view.get("type") in UI_VIEW_TYPES}
    if ui_spec is None:
        if ui_views:
            _finding(findings, "UI-SPEC-MISSING", "blocker", "ui-quality", "ui_spec", "UI views exist without a canonical UI specification.", "Add ui_spec or remove the UI-specific views.", False)
        return set()
    if not isinstance(ui_spec, dict):
        _finding(findings, "STRUCT-UI-SPEC", "blocker", "structure", "ui_spec", "ui_spec must be an object.", "Use the bundled uiSpec schema.", False)
        return set()

    required_sections = ("status", "platforms", "design_system", "personas", "breakpoints", "flows", "screens", "components", "bindings", "navigation", "accessibility", "implementation", "analytics")
    for key in required_sections:
        if key not in ui_spec:
            _finding(findings, "STRUCT-UI-SECTION", "blocker", "structure", f"ui_spec.{key}", f"UI specification section '{key}' is required.", "Add the section using assets/architecture.schema.json.", False)
    if ui_spec.get("status") not in {"not-requested", "draft", "in-review", "approved", "implemented"}:
        _finding(findings, "STRUCT-UI-STATUS", "blocker", "structure", "ui_spec.status", "Unsupported UI specification status.", "Choose not-requested, draft, in-review, approved, or implemented.", False)

    collection_names = ("personas", "breakpoints", "flows", "screens", "components", "bindings", "navigation", "analytics")
    indexes: dict[str, dict[str, dict[str, Any]]] = {}
    ui_ids: set[str] = set()
    for name in collection_names:
        values = ui_spec.get(name, [])
        indexes[name] = {}
        if not isinstance(values, list):
            _finding(findings, "STRUCT-UI-COLLECTION", "blocker", "structure", f"ui_spec.{name}", f"UI section '{name}' must be an array.", "Use an empty array when it does not apply.", False)
            continue
        for index, item in enumerate(values):
            subject = f"ui_spec.{name}[{index}]"
            if not isinstance(item, dict) or not _valid_id(item.get("id")):
                _finding(findings, "STRUCT-UI-ID", "blocker", "structure", subject, "UI item needs a lowercase kebab-case ID.", "Add a stable UI ID.", False)
                continue
            item_id = item["id"]
            if item_id in indexes[name] or item_id in ui_ids or item_id in global_ids:
                _finding(findings, "STRUCT-UI-ID-DUPLICATE", "blocker", "structure", subject, f"UI ID '{item_id}' is not globally unique.", "Use stable, globally unique IDs across architecture and UI elements.", False)
            indexes[name][item_id] = item
            ui_ids.add(item_id)

    active = ui_spec.get("status") != "not-requested"
    if active:
        for name in ("personas", "breakpoints", "flows", "screens", "components"):
            if not indexes.get(name):
                _finding(findings, "UI-SPEC-INCOMPLETE", "blocker", "ui-quality", f"ui_spec.{name}", f"An active UI specification needs at least one {name.replace('_', ' ')} entry.", "Use /grill to define the missing UI scope.", False)

    design_system = ui_spec.get("design_system")
    if not isinstance(design_system, dict):
        _finding(findings, "STRUCT-UI-DESIGN-SYSTEM", "blocker", "structure", "ui_spec.design_system", "design_system must be an object.", "Record the existing design system or an explicit default.", False)
        design_system = {}
    for key in ("name", "source", "reuse_policy", "tokens"):
        if key not in design_system or (key != "tokens" and not _is_nonempty(design_system.get(key))):
            _finding(findings, "UI-DESIGN-SYSTEM-FIELD", "blocker", "ui-quality", f"ui_spec.design_system.{key}", f"Design-system field '{key}' is required.", "Inspect the existing product UI first; otherwise record the chosen default and reuse policy.", False)
    tokens = design_system.get("tokens", {})
    if active and (not isinstance(tokens, dict) or not tokens):
        _finding(findings, "UI-TOKENS-MISSING", "blocker", "ui-quality", "ui_spec.design_system.tokens", "An active UI specification needs implementation-ready design tokens.", "Record semantic color, type, spacing, radius, focus, and surface tokens without hard-coding them into screens.", False)
    elif isinstance(tokens, dict):
        token_names = {str(name).lower() for name in tokens}
        for family in ("color", "type", "space", "radius", "focus"):
            if active and not any(name.startswith(family) for name in token_names):
                _finding(findings, "UI-TOKEN-FAMILY", "warning", "ui-quality", "ui_spec.design_system.tokens", f"No semantic {family} token is recorded.", f"Add at least one {family} token or explain why the design system owns it externally.")

    personas = indexes["personas"]
    for persona_id, persona in personas.items():
        for key in ("name", "goals", "roles", "access_needs"):
            if key not in persona or not _is_nonempty(persona.get(key)):
                _finding(findings, "UI-PERSONA-FIELD", "blocker", "ui-quality", f"ui_spec.personas.{persona_id}.{key}", f"Persona field '{key}' is required.", "Define goals, authorization roles, and access needs.", False)

    breakpoints = indexes["breakpoints"]
    if active and "web" in {str(item).lower() for item in ui_spec.get("platforms", [])} and len(breakpoints) < 2:
        _finding(findings, "UI-RESPONSIVE-BREAKPOINTS", "blocker", "ui-quality", "ui_spec.breakpoints", "A web UI specification needs at least two responsive breakpoints.", "Define compact and wide behavior, including columns and gutters.", False)
    ranges: list[tuple[int, int | None, str]] = []
    for breakpoint_id, breakpoint in breakpoints.items():
        for key in ("label", "min_width", "max_width", "columns", "gutter"):
            if key not in breakpoint:
                _finding(findings, "UI-BREAKPOINT-FIELD", "blocker", "ui-quality", f"ui_spec.breakpoints.{breakpoint_id}.{key}", f"Breakpoint field '{key}' is required.", "Define explicit responsive behavior.", False)
        if isinstance(breakpoint.get("min_width"), int):
            ranges.append((breakpoint["min_width"], breakpoint.get("max_width"), breakpoint_id))
    for index, (left_min, left_max, left_id) in enumerate(ranges):
        for right_min, right_max, right_id in ranges[index + 1 :]:
            left_end = float("inf") if left_max is None else left_max
            right_end = float("inf") if right_max is None else right_max
            if max(left_min, right_min) <= min(left_end, right_end):
                _finding(findings, "UI-BREAKPOINT-OVERLAP", "blocker", "ui-quality", "ui_spec.breakpoints", f"Breakpoints '{left_id}' and '{right_id}' overlap.", "Use non-overlapping inclusive ranges.", False)

    screens = indexes["screens"]
    ui_components = indexes["components"]
    bindings = indexes["bindings"]
    flows = indexes["flows"]

    for component_id, component in ui_components.items():
        for key in ("name", "category", "description", "variants", "states", "props", "events", "accessibility", "implementation", "requirements"):
            if key not in component or (key not in {"variants", "states", "props", "events", "requirements"} and not _is_nonempty(component.get(key))):
                _finding(findings, "UI-COMPONENT-FIELD", "blocker", "ui-quality", f"ui_spec.components.{component_id}.{key}", f"UI component field '{key}' is required.", "Define the component contract and implementation handoff.", False)
        for requirement_id in component.get("requirements", []):
            if requirement_id not in requirements:
                _finding(findings, "STRUCT-REFERENCE", "blocker", "structure", f"ui_spec.components.{component_id}", f"Unknown requirement reference '{requirement_id}'.", "Reference an existing requirement ID.", False)

    screen_region_ids: dict[str, set[str]] = {}
    screen_action_ids: dict[str, set[str]] = {}
    for screen_id, screen in screens.items():
        subject = f"ui_spec.screens.{screen_id}"
        for key in ("name", "route", "purpose", "roles", "data_classification", "requirements", "flows", "states", "regions", "layouts", "evidence"):
            if key not in screen or (key not in {"requirements", "flows", "states", "regions", "layouts", "evidence"} and not _is_nonempty(screen.get(key))):
                _finding(findings, "UI-SCREEN-FIELD", "blocker", "ui-quality", f"{subject}.{key}", f"Screen field '{key}' is required.", "Complete the screen contract.", False)
        for requirement_id in screen.get("requirements", []):
            if requirement_id not in requirements:
                _finding(findings, "STRUCT-REFERENCE", "blocker", "structure", subject, f"Unknown requirement reference '{requirement_id}'.", "Reference an existing requirement ID.", False)
        for flow_id in screen.get("flows", []):
            if flow_id not in flows:
                _finding(findings, "STRUCT-REFERENCE", "blocker", "structure", subject, f"Unknown UI flow '{flow_id}'.", "Reference an existing UI flow ID.", False)
        _validate_evidence(findings, subject, screen.get("evidence", []))

        regions: dict[str, dict[str, Any]] = {}
        action_ids: set[str] = set()
        for index, region in enumerate(screen.get("regions", [])):
            region_subject = f"{subject}.regions[{index}]"
            if not isinstance(region, dict) or not _valid_id(region.get("id")):
                _finding(findings, "STRUCT-UI-REGION-ID", "blocker", "structure", region_subject, "Screen region needs a stable ID.", "Add a lowercase kebab-case ID.", False)
                continue
            region_id = region["id"]
            if region_id in regions:
                _finding(findings, "STRUCT-UI-REGION-DUPLICATE", "blocker", "structure", region_subject, f"Duplicate region '{region_id}'.", "Use one region ID per screen.", False)
            regions[region_id] = region
            if region.get("component") not in ui_components:
                _finding(findings, "STRUCT-REFERENCE", "blocker", "structure", region_subject, f"Unknown UI component '{region.get('component')}'.", "Reference a component from ui_spec.components.", False)
            for binding_id in region.get("bindings", []):
                if binding_id not in bindings:
                    _finding(findings, "STRUCT-REFERENCE", "blocker", "structure", region_subject, f"Unknown UI binding '{binding_id}'.", "Reference a binding from ui_spec.bindings.", False)
            for action in region.get("actions", []):
                if not isinstance(action, dict) or not _valid_id(action.get("id")):
                    _finding(findings, "STRUCT-UI-ACTION-ID", "blocker", "structure", region_subject, "Every interactive action needs a stable ID.", "Add a lowercase kebab-case action ID.", False)
                    continue
                action_id = action["id"]
                if action_id in action_ids:
                    _finding(findings, "STRUCT-UI-ACTION-DUPLICATE", "blocker", "structure", region_subject, f"Duplicate action '{action_id}'.", "Use one action ID per screen.", False)
                action_ids.add(action_id)
                for key in ("label", "kind", "permission", "keyboard"):
                    if not _is_nonempty(action.get(key)):
                        _finding(findings, "UI-ACTION-FIELD", "blocker", "ui-quality", f"{region_subject}.actions.{action_id}.{key}", f"Action field '{key}' is required.", "Define an accessible label, authorization, and keyboard behavior.", False)
                if action.get("target_screen") and action["target_screen"] not in screens:
                    _finding(findings, "STRUCT-REFERENCE", "blocker", "structure", region_subject, f"Unknown target screen '{action['target_screen']}'.", "Reference an existing screen ID.", False)
                if action.get("binding") and action["binding"] not in bindings:
                    _finding(findings, "STRUCT-REFERENCE", "blocker", "structure", region_subject, f"Unknown action binding '{action['binding']}'.", "Reference an existing binding ID.", False)
                if not any(_is_nonempty(action.get(key)) for key in ("target_screen", "target_route", "binding")):
                    _finding(findings, "UI-ACTION-OUTCOME", "blocker", "ui-quality", region_subject, "Interactive action has no navigation or system outcome.", "Set target_screen, target_route, or binding.", False)
                if action.get("kind") == "destructive" and not _is_nonempty(action.get("confirmation")):
                    _finding(findings, "UI-DESTRUCTIVE-CONFIRMATION", "blocker", "ui-quality", region_subject, "Destructive action lacks an explicit confirmation or undo contract.", "Define a confirmation message, impact, and safe recovery path.", False)
        screen_region_ids[screen_id] = set(regions)
        screen_action_ids[screen_id] = action_ids

        states = screen.get("states", [])
        state_ids: set[str] = set()
        state_kinds: set[str] = set()
        for index, state in enumerate(states):
            state_subject = f"{subject}.states[{index}]"
            if not isinstance(state, dict) or not _valid_id(state.get("id")):
                _finding(findings, "STRUCT-UI-STATE-ID", "blocker", "structure", state_subject, "Screen state needs a stable ID.", "Add a lowercase kebab-case state ID.", False)
                continue
            if state["id"] in state_ids:
                _finding(findings, "STRUCT-UI-STATE-DUPLICATE", "blocker", "structure", state_subject, "Duplicate state ID.", "Use one state ID per screen.", False)
            state_ids.add(state["id"])
            state_kinds.add(str(state.get("kind")))
            for key in ("name", "kind", "trigger", "content", "available_actions", "focus_target", "announcement"):
                if key not in state or (key != "available_actions" and not _is_nonempty(state.get(key))):
                    _finding(findings, "UI-STATE-FIELD", "blocker", "ui-quality", f"{state_subject}.{key}", f"State field '{key}' is required.", "Specify content, focus restoration, announcement, and available actions.", False)
            for action_id in state.get("available_actions", []):
                if action_id not in action_ids:
                    _finding(findings, "STRUCT-REFERENCE", "blocker", "structure", state_subject, f"Unknown available action '{action_id}'.", "Reference an action declared on this screen.", False)
        missing_states = set(UI_REQUIRED_STATES) - state_kinds
        if any(binding.get("screen") == screen_id for binding in bindings.values()):
            missing_states |= UI_DATA_STATES - state_kinds
        if screen.get("roles") and "public" not in {str(role).lower() for role in screen.get("roles", [])} and "permission-denied" not in state_kinds:
            missing_states.add("permission-denied")
        if missing_states:
            _finding(findings, "UI-STATE-COVERAGE", "blocker", "ui-quality", subject, "Missing required UI states: " + ", ".join(sorted(missing_states)) + ".", "Specify what the user sees, can do, hears, and where focus moves for every required state.", False)

        layouts = screen.get("layouts", [])
        layout_breakpoints: set[str] = set()
        for index, layout in enumerate(layouts):
            layout_subject = f"{subject}.layouts[{index}]"
            if not isinstance(layout, dict):
                _finding(findings, "STRUCT-UI-LAYOUT", "blocker", "structure", layout_subject, "Layout must be an object.", "Use the uiLayout schema.", False)
                continue
            breakpoint_id = layout.get("breakpoint")
            if breakpoint_id not in breakpoints:
                _finding(findings, "STRUCT-REFERENCE", "blocker", "structure", layout_subject, f"Unknown breakpoint '{breakpoint_id}'.", "Reference a declared UI breakpoint.", False)
            if breakpoint_id in layout_breakpoints:
                _finding(findings, "STRUCT-UI-LAYOUT-DUPLICATE", "blocker", "structure", layout_subject, f"Duplicate layout for '{breakpoint_id}'.", "Keep one layout per screen and breakpoint.", False)
            layout_breakpoints.add(str(breakpoint_id))
            placements: list[dict[str, Any]] = []
            placed_regions: set[str] = set()
            for placement in layout.get("placements", []):
                if not isinstance(placement, dict):
                    _finding(findings, "STRUCT-UI-PLACEMENT", "blocker", "structure", layout_subject, "Region placement must be an object.", "Use region, x, y, w, and h.", False)
                    continue
                region_id = placement.get("region")
                if region_id not in regions:
                    _finding(findings, "STRUCT-REFERENCE", "blocker", "structure", layout_subject, f"Unknown region '{region_id}'.", "Reference a region declared on this screen.", False)
                if region_id in placed_regions:
                    _finding(findings, "STRUCT-UI-PLACEMENT-DUPLICATE", "blocker", "structure", layout_subject, f"Region '{region_id}' is placed twice.", "Keep one placement per region and breakpoint.", False)
                placed_regions.add(str(region_id))
                for key in ("x", "y", "w", "h"):
                    if not isinstance(placement.get(key), (int, float)):
                        _finding(findings, "STRUCT-UI-GEOMETRY", "blocker", "structure", layout_subject, f"Placement '{key}' must be numeric.", "Supply explicit wireframe coordinates.", False)
                if all(isinstance(placement.get(key), (int, float)) for key in ("x", "y", "w", "h")):
                    if placement["x"] + placement["w"] > layout.get("width", 0) or placement["y"] + placement["h"] > layout.get("height", 0):
                        _finding(findings, "UI-PLACEMENT-BOUNDS", "blocker", "ui-quality", layout_subject, f"Region '{region_id}' exceeds the layout canvas.", "Move or resize the region within the breakpoint canvas.", False)
                    placements.append(placement)
            missing_regions = set(regions) - placed_regions
            if missing_regions:
                _finding(findings, "UI-REGION-NOT-PLACED", "blocker", "ui-quality", layout_subject, "Regions missing from layout: " + ", ".join(sorted(missing_regions)) + ".", "Place every visible region or split conditional variants into separate screens/states.", False)
            for left_index, left in enumerate(placements):
                for right in placements[left_index + 1 :]:
                    if _rect_overlap(left, right, 0):
                        _finding(findings, "UI-REGION-OVERLAP", "blocker", "ui-quality", layout_subject, f"Regions '{left.get('region')}' and '{right.get('region')}' overlap.", "Use non-overlapping wireframe geometry.", False)
        if active and breakpoints and layout_breakpoints != set(breakpoints):
            _finding(findings, "UI-RESPONSIVE-COVERAGE", "blocker", "ui-quality", subject, "Screen layouts do not cover every declared breakpoint.", "Define each screen at every supported breakpoint or reduce the global breakpoint set.", False)

    for binding_id, binding in bindings.items():
        subject = f"ui_spec.bindings.{binding_id}"
        for key in ("screen", "region", "architecture_component", "operation", "transport", "request", "response", "authorization", "loading", "error", "requirements"):
            if key not in binding or (key != "requirements" and not _is_nonempty(binding.get(key))):
                _finding(findings, "UI-BINDING-FIELD", "blocker", "ui-quality", f"{subject}.{key}", f"Binding field '{key}' is required.", "Define the end-to-end UI-to-system contract.", False)
        screen_id = binding.get("screen")
        if screen_id not in screens:
            _finding(findings, "STRUCT-REFERENCE", "blocker", "structure", subject, f"Unknown screen '{screen_id}'.", "Reference an existing UI screen.", False)
        elif binding.get("region") not in screen_region_ids.get(str(screen_id), set()):
            _finding(findings, "STRUCT-REFERENCE", "blocker", "structure", subject, f"Unknown region '{binding.get('region')}' on screen '{screen_id}'.", "Reference a region declared on that screen.", False)
        if binding.get("architecture_component") not in architecture_components:
            _finding(findings, "STRUCT-REFERENCE", "blocker", "structure", subject, f"Unknown architecture component '{binding.get('architecture_component')}'.", "Link the UI operation to the backend or platform component that serves it.", False)
        if binding.get("relationship") and binding["relationship"] not in relationships:
            _finding(findings, "STRUCT-REFERENCE", "blocker", "structure", subject, f"Unknown architecture relationship '{binding['relationship']}'.", "Reference the corresponding connection contract.", False)
        for requirement_id in binding.get("requirements", []):
            if requirement_id not in requirements:
                _finding(findings, "STRUCT-REFERENCE", "blocker", "structure", subject, f"Unknown requirement reference '{requirement_id}'.", "Reference an existing requirement ID.", False)

    for flow_id, flow in flows.items():
        subject = f"ui_spec.flows.{flow_id}"
        for key in ("name", "actor", "goal", "entry_screens", "preconditions", "steps", "outcomes", "exceptions", "requirements"):
            if key not in flow or (key not in {"preconditions", "outcomes", "exceptions", "requirements"} and not _is_nonempty(flow.get(key))):
                _finding(findings, "UI-FLOW-FIELD", "blocker", "ui-quality", f"{subject}.{key}", f"Flow field '{key}' is required.", "Define the user goal, success path, and exception paths.", False)
        if flow.get("actor") not in personas:
            _finding(findings, "STRUCT-REFERENCE", "blocker", "structure", subject, f"Unknown persona '{flow.get('actor')}'.", "Reference a UI persona ID.", False)
        for screen_id in flow.get("entry_screens", []):
            if screen_id not in screens:
                _finding(findings, "STRUCT-REFERENCE", "blocker", "structure", subject, f"Unknown entry screen '{screen_id}'.", "Reference an existing UI screen.", False)
        step_ids: set[str] = set()
        for index, step in enumerate(flow.get("steps", [])):
            step_subject = f"{subject}.steps[{index}]"
            if not isinstance(step, dict) or not _valid_id(step.get("id")):
                _finding(findings, "STRUCT-UI-FLOW-STEP", "blocker", "structure", step_subject, "Flow step needs a stable ID.", "Add a lowercase kebab-case step ID.", False)
                continue
            if step["id"] in step_ids:
                _finding(findings, "STRUCT-UI-FLOW-STEP-DUPLICATE", "blocker", "structure", step_subject, "Duplicate flow-step ID.", "Use a unique step ID within the flow.", False)
            step_ids.add(step["id"])
            if step.get("screen") not in screens:
                _finding(findings, "STRUCT-REFERENCE", "blocker", "structure", step_subject, f"Unknown step screen '{step.get('screen')}'.", "Reference an existing UI screen.", False)
            for key in ("action", "outcome"):
                if not _is_nonempty(step.get(key)):
                    _finding(findings, "UI-FLOW-STEP-FIELD", "blocker", "ui-quality", f"{step_subject}.{key}", f"Flow-step field '{key}' is required.", "State the user action and observable outcome.", False)
        for requirement_id in flow.get("requirements", []):
            if requirement_id not in requirements:
                _finding(findings, "STRUCT-REFERENCE", "blocker", "structure", subject, f"Unknown requirement reference '{requirement_id}'.", "Reference an existing requirement ID.", False)

    for navigation_id, navigation in indexes["navigation"].items():
        subject = f"ui_spec.navigation.{navigation_id}"
        for endpoint in ("from", "to"):
            if navigation.get(endpoint) not in screens:
                _finding(findings, "STRUCT-REFERENCE", "blocker", "structure", subject, f"Unknown navigation {endpoint} screen '{navigation.get(endpoint)}'.", "Reference an existing UI screen.", False)
        for key in ("trigger", "condition", "guard", "back_behavior"):
            if not _is_nonempty(navigation.get(key)):
                _finding(findings, "UI-NAVIGATION-FIELD", "blocker", "ui-quality", f"{subject}.{key}", f"Navigation field '{key}' is required.", "Define route guards and back/refresh behavior.", False)
        for requirement_id in navigation.get("requirements", []):
            if requirement_id not in requirements:
                _finding(findings, "STRUCT-REFERENCE", "blocker", "structure", subject, f"Unknown requirement reference '{requirement_id}'.", "Reference an existing requirement ID.", False)

    accessibility = ui_spec.get("accessibility")
    if not isinstance(accessibility, dict):
        _finding(findings, "STRUCT-UI-ACCESSIBILITY", "blocker", "structure", "ui_spec.accessibility", "Accessibility must be an object.", "Use the uiAccessibility schema.", False)
        accessibility = {}
    for key in ("target", "keyboard", "focus", "screen_reader", "contrast", "zoom_reflow", "reduced_motion", "testing"):
        if key not in accessibility or not _is_nonempty(accessibility.get(key)):
            _finding(findings, "UI-ACCESSIBILITY-FIELD", "blocker", "ui-quality", f"ui_spec.accessibility.{key}", f"Accessibility field '{key}' is required.", "Define implementation and verification behavior, not only a conformance label.", False)
    target = str(accessibility.get("target", "")).lower()
    if active and ("wcag 2.2" not in target or "aa" not in target):
        _finding(findings, "UI-WCAG-TARGET", "blocker", "ui-quality", "ui_spec.accessibility.target", "The UI target is not WCAG 2.2 Level AA.", "Adopt WCAG 2.2 AA unless the governing standard is stricter.", False)
    tests = " ".join(str(item).lower() for item in accessibility.get("testing", []))
    for technique in ("keyboard", "screen reader", "automated"):
        if active and technique not in tests:
            _finding(findings, "UI-ACCESSIBILITY-TESTING", "blocker", "ui-quality", "ui_spec.accessibility.testing", f"Accessibility verification does not include {technique} testing.", "Add the missing test method and ownership to the acceptance plan.", False)

    implementation = ui_spec.get("implementation")
    if not isinstance(implementation, dict):
        _finding(findings, "STRUCT-UI-IMPLEMENTATION", "blocker", "structure", "ui_spec.implementation", "Implementation handoff must be an object.", "Use the uiImplementation schema.", False)
        implementation = {}
    for key in ("front_end", "design_system_package", "state_management", "data_fetching", "validation", "testing", "feature_flags", "observability"):
        if active and not _is_nonempty(implementation.get(key)):
            _finding(findings, "UI-IMPLEMENTATION-FIELD", "blocker", "ui-quality", f"ui_spec.implementation.{key}", f"Implementation field '{key}' is required.", "Record the chosen approach or a bounded decision owner.", False)

    for analytics_id, analytics in indexes["analytics"].items():
        subject = f"ui_spec.analytics.{analytics_id}"
        if analytics.get("screen") not in screens:
            _finding(findings, "STRUCT-REFERENCE", "blocker", "structure", subject, f"Unknown analytics screen '{analytics.get('screen')}'.", "Reference an existing UI screen.", False)
        for key in ("event", "trigger", "properties", "privacy"):
            if key not in analytics or (key != "properties" and not _is_nonempty(analytics.get(key))):
                _finding(findings, "UI-ANALYTICS-FIELD", "blocker", "ui-quality", f"{subject}.{key}", f"Analytics field '{key}' is required.", "Define a stable event, trigger, permitted properties, and privacy rule.", False)

    for view_id, view in ui_views.items():
        subject = f"views.{view_id}"
        view_type = view.get("type")
        if view_type == "user-flow":
            if view.get("flow") not in flows:
                _finding(findings, "UI-VIEW-FLOW", "blocker", "ui-quality", subject, "User-flow view does not reference a known flow.", "Set view.flow to a ui_spec.flows ID.", False)
        elif view_type in {"ui-wireframe", "ui-state-map"}:
            screen = screens.get(view.get("screen"))
            if not screen:
                _finding(findings, "UI-VIEW-SCREEN", "blocker", "ui-quality", subject, "UI view does not reference a known screen.", "Set view.screen to a ui_spec.screens ID.", False)
            if view_type == "ui-wireframe":
                if view.get("breakpoint") not in breakpoints:
                    _finding(findings, "UI-VIEW-BREAKPOINT", "blocker", "ui-quality", subject, "Wireframe view does not reference a known breakpoint.", "Set view.breakpoint to a ui_spec.breakpoints ID.", False)
                if screen and not any(layout.get("breakpoint") == view.get("breakpoint") for layout in screen.get("layouts", [])):
                    _finding(findings, "UI-VIEW-LAYOUT", "blocker", "ui-quality", subject, "Wireframe view has no matching screen layout.", "Add that breakpoint layout to the screen.", False)
                if view.get("state") and screen and view["state"] not in {state.get("id") for state in screen.get("states", []) if isinstance(state, dict)}:
                    _finding(findings, "UI-VIEW-STATE", "blocker", "ui-quality", subject, f"Unknown screen state '{view['state']}'.", "Reference a state declared on the screen.", False)

    if active:
        wireframe_pairs = {(view.get("screen"), view.get("breakpoint")) for view in ui_views.values() if view.get("type") == "ui-wireframe"}
        for screen_id, screen in screens.items():
            for layout in screen.get("layouts", []):
                pair = (screen_id, layout.get("breakpoint"))
                if pair not in wireframe_pairs:
                    _finding(findings, "UI-WIREFRAME-COVERAGE", "warning", "ui-quality", f"ui_spec.screens.{screen_id}", f"No draw.io wireframe page exists for breakpoint '{layout.get('breakpoint')}'.", "Add a ui-wireframe view for complete visual review coverage.")
        flow_views = {view.get("flow") for view in ui_views.values() if view.get("type") == "user-flow"}
        for flow_id in flows:
            if flow_id not in flow_views:
                _finding(findings, "UI-FLOW-VIEW-COVERAGE", "warning", "ui-quality", f"ui_spec.flows.{flow_id}", "Flow has no draw.io user-flow page.", "Add a user-flow view for the implementation and review pack.")
    return ui_ids


def _validate_waiver_shape(findings: list[Finding], waivers: dict[str, dict[str, Any]]) -> None:
    for waiver_id, waiver in waivers.items():
        subject = f"waivers.{waiver_id}"
        for key in ("finding_code", "scope", "rationale", "compensating_controls", "owner", "approver", "expires"):
            if key not in waiver or not _is_nonempty(waiver.get(key)):
                _finding(findings, "STRUCT-WAIVER-FIELD", "blocker", "structure", f"{subject}.{key}", f"Waiver field '{key}' is required.", "Complete or remove the waiver.", False)
        if waiver.get("expires") and not _is_date(waiver.get("expires")):
            _finding(findings, "STRUCT-DATE", "blocker", "structure", f"{subject}.expires", "Waiver expiry is not an ISO date.", "Use YYYY-MM-DD.", False)


def audit_model(model: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    project = model.get("project", {}) if isinstance(model.get("project"), dict) else {}
    requirements = {item.get("id"): item for item in model.get("requirements", []) if isinstance(item, dict) and item.get("id")}
    controls = {item.get("id"): item for item in model.get("controls", []) if isinstance(item, dict) and item.get("id")}
    components = {item.get("id"): item for item in model.get("components", []) if isinstance(item, dict) and item.get("id")}
    production = "prod" in {str(item).lower() for item in project.get("environments", [])}

    blocking_questions = [q for q in model.get("open_questions", []) if isinstance(q, dict) and q.get("blocking") and q.get("status") == "open"]
    for question in blocking_questions:
        _finding(findings, "DISC-BLOCKING-QUESTION", "blocker", "discovery", f"open_questions.{question.get('id', 'unknown')}", question.get("question", "A blocking architecture question remains open."), "Resolve it through /grill or explicitly reclassify it with owner and consequence.", False)

    for requirement in requirements.values():
        if requirement.get("priority") == "must" and requirement.get("status") == "unresolved":
            _finding(findings, "DISC-MUST-UNRESOLVED", "blocker", "discovery", f"requirements.{requirement['id']}", "A must-have requirement is unresolved.", "Resolve it, accept a bounded assumption, or mark it non-applicable with rationale.", False)

    must_types = {item.get("type") for item in requirements.values() if item.get("priority") == "must" and item.get("status") in {"confirmed", "evidenced", "assumed"}}
    accepted_types = {item.get("type") for item in requirements.values() if item.get("status") in {"confirmed", "evidenced", "assumed"}}
    for req_type in ("availability", "security", "data", "operations"):
        if production and req_type not in must_types:
            _finding(findings, f"DISC-REQ-{req_type.upper()}", "blocker", "discovery", "requirements", f"Production design has no accepted must-level {req_type} requirement.", f"Use /grill to define the {req_type} acceptance target.", False)
    for req_type in ("performance", "cost"):
        if production and req_type not in accepted_types:
            _finding(findings, f"DISC-REQ-{req_type.upper()}", "warning", "discovery", "requirements", f"Production design has no accepted {req_type} requirement.", f"Define an acceptance target or explain non-applicability.")

    traced_requirements: set[str] = set()
    for collection in (model.get("components", []), model.get("relationships", []), model.get("controls", []), model.get("views", [])):
        for item in collection:
            if isinstance(item, dict):
                traced_requirements.update(item.get("requirements", []))
    ui_spec = model.get("ui_spec", {}) if isinstance(model.get("ui_spec"), dict) else {}
    for collection_name in ("screens", "flows", "components", "bindings", "navigation"):
        for item in ui_spec.get(collection_name, []):
            if isinstance(item, dict):
                traced_requirements.update(item.get("requirements", []))
    for requirement in requirements.values():
        if requirement.get("priority") == "must" and requirement["id"] not in traced_requirements:
            _finding(findings, "TRACE-ORPHAN-MUST", "blocker", "traceability", f"requirements.{requirement['id']}", "Must requirement is not traced to a component, connection, control, or view.", "Add requirement references to the elements that satisfy or explain it.")

    for component_id, component in components.items():
        subject = f"components.{component_id}"
        if str(component.get("owner", "")).strip().lower() in {"", "tbd", "unknown", "unassigned"}:
            _finding(findings, "GOV-OWNER", "blocker" if production else "warning", "governance", subject, "Component ownership is unresolved.", "Assign an accountable team or role.")
        if component.get("public_exposure") == "unknown":
            _finding(findings, "SEC-EXPOSURE-UNKNOWN", "blocker", "security", subject, "Public exposure is unknown.", "Decide whether the component is public, private, or not network exposed.", False)
        if component.get("kind") in DATA_STORES and component.get("data_classification") in SENSITIVE and component.get("public_exposure") not in {"none", "private"}:
            _finding(findings, "SEC-SENSITIVE-STORE-PUBLIC", "blocker", "security", subject, "Sensitive data store is not explicitly private.", "Disable public access and use private connectivity.", False)
        if component.get("kind") not in {"actor", "external-system"} and component.get("criticality") in {"high", "mission-critical"} and production and not _is_nonempty(component.get("scaling")):
            _finding(findings, "REL-SCALING-UNDEFINED", "warning", "reliability", subject, "High-criticality component has no scaling or capacity statement.", "Record fixed capacity, autoscaling bounds, or why scaling is not applicable.")
        if not component.get("evidence"):
            _finding(findings, "EVIDENCE-COMPONENT-EMPTY", "warning", "evidence", subject, "Component has no evidence or proposal marker.", "Add user, repository, runtime, inference, or proposal evidence with confidence.")

    for relationship in model.get("relationships", []):
        if not isinstance(relationship, dict) or not relationship.get("id"):
            continue
        subject = f"relationships.{relationship['id']}"
        source = components.get(relationship.get("from"), {})
        target = components.get(relationship.get("to"), {})
        sensitive_flow = any(any(token in str(item).lower() for token in ("pii", "phi", "pci", "secret", "confidential", "restricted")) for item in relationship.get("data", [])) or source.get("data_classification") in SENSITIVE or target.get("data_classification") in SENSITIVE
        if sensitive_flow and not relationship.get("encrypted"):
            _finding(findings, "SEC-SENSITIVE-FLOW-UNENCRYPTED", "blocker", "security", subject, "Sensitive flow is not encrypted in transit.", "Use an approved encrypted protocol and record TLS or equivalent.", False)
        if relationship.get("auth", "").strip().lower() in {"", "none", "unknown"} and (source.get("public_exposure") == "public" or target.get("public_exposure") == "public"):
            _finding(findings, "SEC-PUBLIC-FLOW-NO-AUTH", "blocker", "security", subject, "Public flow has no explicit authentication.", "Define authentication or explicitly justify an anonymous public endpoint with compensating controls.", False)
        if relationship.get("mode") == "sync" and not _is_nonempty(relationship.get("timeout")):
            _finding(findings, "REL-SYNC-TIMEOUT", "warning", "reliability", subject, "Synchronous dependency has no timeout budget.", "Define a bounded timeout and retry interaction.")
        if relationship.get("mode") in {"async", "stream"}:
            for key, code, label in (
                ("retry", "REL-ASYNC-RETRY", "retry and poison-message behavior"),
                ("idempotency", "REL-ASYNC-IDEMPOTENCY", "idempotency or deduplication behavior"),
                ("ordering", "REL-ASYNC-ORDERING", "ordering scope or non-requirement"),
            ):
                if not _is_nonempty(relationship.get(key)):
                    _finding(findings, code, "warning", "reliability", subject, f"Asynchronous flow has no {label}.", f"Record {label}.")

    if str(project.get("cloud_provider", "")).lower() == "azure":
        _audit_azure(findings, model, production)
    elif project.get("cloud_provider"):
        _finding(findings, "CLOUD-NON-AZURE-GENERIC", "warning", "governance", "project.cloud_provider", "This package has deterministic governance rules only for Azure; other providers render with generic symbols.", "Use the selected provider's governance review and record the result separately.")

    kubernetes = dig(model, "platform", "kubernetes", default={})
    if isinstance(kubernetes, dict) and kubernetes.get("enabled"):
        _audit_kubernetes(findings, kubernetes, production)

    _audit_delivery_operations(findings, model, production)
    return findings


def _require_path(
    findings: list[Finding],
    root: dict[str, Any],
    path: tuple[str, ...],
    code: str,
    level: str,
    gate: str,
    remediation: str,
    expected: Any | None = None,
    waiver_allowed: bool = True,
) -> None:
    value = dig(root, *path)
    missing = not _is_nonempty(value)
    if expected is not None:
        missing = value != expected
    if missing:
        dotted = ".".join(path)
        expectation = f" set to {expected!r}" if expected is not None else " defined"
        _finding(findings, code, level, gate, dotted, f"Required architecture control '{dotted}' is not{expectation}.", remediation, waiver_allowed)


def _audit_azure(findings: list[Finding], model: dict[str, Any], production: bool) -> None:
    azure = dig(model, "platform", "azure", default={})
    if not isinstance(azure, dict):
        _finding(findings, "AZ-PLATFORM", "blocker", "azure", "platform.azure", "Azure platform configuration is missing.", "Complete landing-zone, network, identity, security, reliability, and cost fields.", False)
        return
    level = "blocker" if production else "warning"
    requirements = (
        (("landing_zone", "management_group"), "AZ-LZ-MG", level, "governance", "Record the target management group or accepted application landing-zone scope.", None, True),
        (("landing_zone", "subscription_strategy"), "AZ-LZ-SUBSCRIPTION", level, "governance", "Define subscription and environment separation.", None, True),
        (("landing_zone", "policy_scope"), "AZ-LZ-POLICY", level, "governance", "Define Azure Policy assignment and exemption scope.", None, True),
        (("landing_zone", "budgets"), "AZ-LZ-BUDGET", "warning", "cost", "Define budgets and alerts.", True, True),
        (("network", "topology"), "AZ-NET-TOPOLOGY", level, "network", "Choose and own hub-spoke, Virtual WAN, or an explicit simpler topology.", None, True),
        (("network", "ingress"), "AZ-NET-INGRESS", level, "network", "Define the ingress service and origin restriction.", None, True),
        (("network", "egress"), "AZ-NET-EGRESS", level, "network", "Define egress control and ownership.", None, True),
        (("network", "dns"), "AZ-NET-DNS", level, "network", "Define public and private DNS ownership and resolution path.", None, True),
        (("network", "private_endpoints"), "AZ-NET-PRIVATE-ENDPOINTS", level, "security", "Use private endpoints for sensitive PaaS data services or document the exception.", True, True),
        (("network", "controlled_egress"), "AZ-NET-CONTROLLED-EGRESS", level, "security", "Route outbound traffic through an observable policy control.", True, True),
        (("network", "waf"), "AZ-NET-WAF", level, "security", "Protect public HTTP ingress with WAF or state non-applicability.", True, True),
        (("network", "ddos"), "AZ-NET-DDOS", "warning", "security", "Record the DDoS protection decision for public ingress.", True, True),
        (("identity", "human"), "AZ-ID-HUMAN", level, "identity", "Define Entra-based human authentication and access governance.", None, False),
        (("identity", "workload"), "AZ-ID-WORKLOAD", level, "identity", "Use managed identity or Entra Workload ID.", None, False),
        (("identity", "least_privilege_rbac"), "AZ-ID-RBAC", level, "identity", "Use least-privilege Azure and workload RBAC.", True, False),
        (("identity", "pim"), "AZ-ID-PIM", level, "identity", "Use PIM or a documented JIT privileged-access control.", True, True),
        (("identity", "secrets_store"), "AZ-ID-SECRETS", level, "identity", "Use Key Vault or an approved managed secret store.", None, False),
        (("identity", "break_glass"), "AZ-ID-BREAKGLASS", "warning", "identity", "Define monitored break-glass access.", True, True),
        (("security", "defender"), "AZ-SEC-DEFENDER", "warning", "security", "Enable Defender plans or document an equivalent control.", True, True),
        (("security", "sentinel"), "AZ-SEC-SIEM", "warning", "security", "Integrate with Sentinel or the approved SIEM.", True, True),
        (("security", "encryption_in_transit"), "AZ-SEC-TLS", level, "security", "Require encryption in transit.", True, False),
        (("security", "encryption_at_rest"), "AZ-SEC-AT-REST", level, "security", "Require encryption at rest and decide CMK ownership.", True, False),
        (("security", "diagnostic_settings"), "AZ-SEC-DIAGNOSTICS", level, "operations", "Route required resource and activity logs to the approved destinations.", True, True),
        (("reliability", "restore_tested"), "AZ-REL-RESTORE", level, "reliability", "Test restore against RTO and RPO; backup success alone is insufficient.", True, True),
        (("cost", "owner"), "AZ-COST-OWNER", "warning", "cost", "Assign FinOps or workload cost ownership.", None, True),
        (("cost", "right_sizing"), "AZ-COST-RIGHTSIZING", "warning", "cost", "Define right-sizing and review cadence.", True, True),
        (("cost", "anomaly_alerts"), "AZ-COST-ANOMALY", "warning", "cost", "Enable cost anomaly detection or an equivalent alert.", True, True),
    )
    for path, code, item_level, gate, remediation, expected, waiver_allowed in requirements:
        _require_path(findings, azure, path, code, item_level, gate, remediation, expected, waiver_allowed)

    tags = dig(azure, "landing_zone", "tags_required", default=[])
    required_tags = {"owner", "application", "environment", "cost-center", "data-classification", "criticality"}
    normalized_tags = {str(tag).strip().lower() for tag in tags} if isinstance(tags, list) else set()
    missing_tags = sorted(required_tags - normalized_tags)
    if missing_tags:
        _finding(findings, "AZ-LZ-TAGS", "warning", "governance", "platform.azure.landing_zone.tags_required", f"Required governance tags are missing: {', '.join(missing_tags)}.", "Add the tags or map them to tenant-standard equivalents.")

    if dig(azure, "reliability", "multi_region"):
        for path, code, remediation in (
            (("reliability", "failover_runbook"), "AZ-REL-FAILOVER-RUNBOOK", "Define traffic, data, and operational failover steps."),
            (("reliability", "failover_test_cadence"), "AZ-REL-FAILOVER-TEST", "Define and own regular failover exercises."),
            (("reliability", "data_consistency"), "AZ-REL-DATA-CONSISTENCY", "Define consistency and split-brain behavior."),
        ):
            _require_path(findings, azure, path, code, level, "reliability", remediation)


def _audit_kubernetes(findings: list[Finding], kubernetes: dict[str, Any], production: bool) -> None:
    level = "blocker" if production else "warning"
    requirements = (
        (("justification",), "K8S-JUSTIFICATION", level, "kubernetes", "Record why Kubernetes is preferable to a simpler managed runtime.", None, True),
        (("private_cluster",), "K8S-PRIVATE-CLUSTER", level, "kubernetes-security", "Use a private production API server or document restricted public access.", True, True),
        (("supported_version_policy",), "K8S-VERSION-POLICY", level, "kubernetes-operations", "Define supported-version and node OS policy.", None, True),
        (("upgrade_channel",), "K8S-UPGRADE-CHANNEL", level, "kubernetes-operations", "Define upgrade channel and ownership.", None, True),
        (("maintenance_window",), "K8S-MAINTENANCE", "warning", "kubernetes-operations", "Define a maintenance window and disruption expectations.", None, True),
        (("workload_defaults", "replicas_min"), "K8S-REPLICAS", level, "kubernetes-reliability", "Use at least two replicas for availability-sensitive stateless production workloads.", None, True),
        (("workload_defaults", "readiness_probe"), "K8S-READINESS", level, "kubernetes-reliability", "Require a readiness probe.", True, True),
        (("workload_defaults", "liveness_probe"), "K8S-LIVENESS", level, "kubernetes-reliability", "Require a liveness probe with a distinct purpose.", True, True),
        (("workload_defaults", "startup_probe"), "K8S-STARTUP", "warning", "kubernetes-reliability", "Use startup probes for workloads whose initialization can exceed liveness timing.", True, True),
        (("workload_defaults", "requests_limits"), "K8S-RESOURCES", level, "kubernetes-reliability", "Define measured requests and limits.", True, True),
        (("workload_defaults", "pdb"), "K8S-PDB", level, "kubernetes-reliability", "Define PodDisruptionBudgets for availability-sensitive workloads.", True, True),
        (("workload_defaults", "topology_spread"), "K8S-TOPOLOGY", level, "kubernetes-reliability", "Spread replicas across failure domains.", True, True),
        (("workload_defaults", "graceful_termination"), "K8S-TERMINATION", "warning", "kubernetes-reliability", "Define graceful termination and connection draining.", True, True),
        (("network", "default_deny"), "K8S-NETPOL-DEFAULT-DENY", level, "kubernetes-security", "Use default-deny ingress and egress with explicit allowances.", True, False),
        (("network", "controlled_egress"), "K8S-EGRESS", level, "kubernetes-security", "Control and observe workload egress.", True, True),
        (("security", "pod_security_standard"), "K8S-PSS", level, "kubernetes-security", "Enforce the Restricted Pod Security Standard or document exceptions.", "restricted", False),
        (("security", "run_as_non_root"), "K8S-NONROOT", level, "kubernetes-security", "Run workloads as non-root.", True, False),
        (("security", "allow_privilege_escalation"), "K8S-PRIVESC", level, "kubernetes-security", "Set allowPrivilegeEscalation to false.", False, False),
        (("security", "seccomp_runtime_default"), "K8S-SECCOMP", level, "kubernetes-security", "Use RuntimeDefault seccomp.", True, False),
        (("security", "drop_all_capabilities"), "K8S-CAPABILITIES", level, "kubernetes-security", "Drop all Linux capabilities and add back only reviewed exceptions.", True, False),
        (("security", "workload_identity"), "K8S-WORKLOAD-ID", level, "kubernetes-security", "Use Microsoft Entra Workload ID.", True, False),
        (("security", "external_secrets"), "K8S-EXTERNAL-SECRETS", level, "kubernetes-security", "Deliver secrets from Key Vault or an approved external secret store.", True, False),
        (("supply_chain", "digest_pinning"), "K8S-IMAGE-DIGEST", level, "supply-chain", "Promote immutable images pinned by digest.", True, True),
        (("supply_chain", "image_scanning"), "K8S-IMAGE-SCAN", level, "supply-chain", "Scan images and enforce severity policy.", True, True),
        (("supply_chain", "sbom"), "K8S-SBOM", "warning", "supply-chain", "Generate and retain an SBOM.", True, True),
        (("supply_chain", "signing"), "K8S-SIGNING", "warning", "supply-chain", "Sign images and verify provenance at admission.", True, True),
        (("operations", "gitops"), "K8S-GITOPS", level, "kubernetes-operations", "Use GitOps or an equivalently controlled declarative delivery path.", None, True),
        (("operations", "backup_restore"), "K8S-BACKUP-RESTORE", level, "kubernetes-operations", "Define and test workload and platform recovery.", None, True),
        (("operations", "observability"), "K8S-OBSERVABILITY", level, "kubernetes-operations", "Collect workload, cluster, control-plane, and audit telemetry.", None, True),
    )
    for path, code, item_level, gate, remediation, expected, waiver_allowed in requirements:
        _require_path(findings, kubernetes, path, code, item_level, gate, remediation, expected, waiver_allowed)
    replicas = dig(kubernetes, "workload_defaults", "replicas_min")
    if production and isinstance(replicas, int) and replicas < 2:
        _finding(findings, "K8S-REPLICAS", "blocker", "kubernetes-reliability", "platform.kubernetes.workload_defaults.replicas_min", "Minimum replicas is below two for production.", "Use at least two for availability-sensitive stateless services or scope a justified waiver.")
    zones = kubernetes.get("zones")
    if production and (not isinstance(zones, int) or zones < 2):
        _finding(findings, "K8S-ZONES", "warning", "kubernetes-reliability", "platform.kubernetes.zones", "Production AKS is not explicitly spread across at least two availability zones.", "Use zonal pools when supported and justified, or document the availability tradeoff.")


def _audit_delivery_operations(findings: list[Finding], model: dict[str, Any], production: bool) -> None:
    delivery = dig(model, "platform", "delivery", default={})
    operations = dig(model, "platform", "operations", default={})
    level = "blocker" if production else "warning"
    for path, code, item_level, remediation, expected in (
        (("iac",), "OPS-IAC", level, "Define infrastructure as code and ownership.", None),
        (("ci_cd",), "OPS-CICD", level, "Define the build and deployment system.", None),
        (("immutable_artifacts",), "OPS-IMMUTABLE", level, "Promote immutable artifacts across environments.", True),
        (("policy_gates",), "OPS-POLICY-GATES", "warning", "Add policy, security, and quality gates.", True),
        (("health_verification",), "OPS-HEALTH-VERIFY", level, "Define automated post-deployment verification.", True),
        (("rollback",), "OPS-ROLLBACK", level, "Define tested rollback or roll-forward behavior.", None),
    ):
        _require_path(findings, delivery if isinstance(delivery, dict) else {}, path, code, item_level, "delivery", remediation, expected)
    for path, code, item_level, remediation, expected in (
        (("logs",), "OBS-LOGS", level, "Define structured logs and retention.", None),
        (("metrics",), "OBS-METRICS", level, "Define metrics and ownership.", None),
        (("traces",), "OBS-TRACES", "warning", "Define distributed tracing or explain non-applicability.", None),
        (("slos",), "OBS-SLOS", level, "Define user-facing SLOs and error budgets.", None),
        (("alerts",), "OBS-ALERTS", level, "Define actionable alerts and owners.", None),
        (("runbooks",), "OBS-RUNBOOKS", level, "Define runbooks and escalation.", None),
        (("backup_restore_tested",), "OPS-RESTORE-TEST", level, "Test restore against stated RTO and RPO.", True),
    ):
        _require_path(findings, operations if isinstance(operations, dict) else {}, path, code, item_level, "operations", remediation, expected)


def apply_waivers(findings: Iterable[Finding], model: dict[str, Any], today: date | None = None) -> list[Finding]:
    result = [copy.copy(item) for item in findings]
    waiver_items = [item for item in model.get("waivers", []) if isinstance(item, dict)]
    current = today or date.today()
    for finding in result:
        if finding.level != "blocker" or not finding.waiver_allowed:
            continue
        for waiver in waiver_items:
            if waiver.get("finding_code") != finding.code:
                continue
            if waiver.get("scope") not in {"*", finding.subject}:
                continue
            if not all(_is_nonempty(waiver.get(key)) for key in ("id", "rationale", "compensating_controls", "owner", "approver", "expires")):
                continue
            try:
                expiry = date.fromisoformat(str(waiver["expires"])[:10])
            except ValueError:
                continue
            if expiry < current:
                continue
            finding.waived_by = str(waiver["id"])
            break
    return result


def all_findings(model: dict[str, Any], icon_ids: set[str] | None = None) -> list[Finding]:
    structural = validate_structure(model, icon_ids)
    if any(item.level == "blocker" and item.gate == "structure" for item in structural):
        return apply_waivers(structural, model)
    return apply_waivers([*structural, *audit_model(model)], model)


def finding_summary(findings: Iterable[Finding]) -> dict[str, Any]:
    items = list(findings)
    blockers = [item for item in items if item.blocking]
    waived = [item for item in items if item.waived_by]
    return {
        "status": "pass" if not blockers else "fail",
        "blocking": len(blockers),
        "waived": len(waived),
        "warnings": sum(1 for item in items if item.level == "warning"),
        "info": sum(1 for item in items if item.level == "info"),
        "total": len(items),
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    }
