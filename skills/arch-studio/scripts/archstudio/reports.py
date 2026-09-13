from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone
from typing import Any, Iterable

from .model import Finding, finding_summary, model_digest


def governance_json(model: dict[str, Any], findings: Iterable[Finding]) -> bytes:
    items = list(findings)
    payload = {
        "schema_version": "1.0",
        "project_id": model.get("project", {}).get("id"),
        "project_version": model.get("project", {}).get("version"),
        "model_sha256": model_digest(model),
        "summary": finding_summary(items),
        "findings": [item.to_dict() for item in items],
        "scope": "Design-time assessment of the canonical model; not live Azure or Kubernetes compliance evidence.",
    }
    return (json.dumps(payload, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def governance_markdown(model: dict[str, Any], findings: Iterable[Finding]) -> bytes:
    items = list(findings)
    summary = finding_summary(items)
    project = model.get("project", {})
    lines = [
        f"# Governance review: {project.get('title', project.get('id', 'Architecture'))}",
        "",
        f"- Project: `{project.get('id', '')}`",
        f"- Version: `{project.get('version', '')}`",
        f"- Model SHA-256: `{model_digest(model)}`",
        f"- Gate: **{summary['status'].upper()}**",
        f"- Blocking: {summary['blocking']} · Waived: {summary['waived']} · Warnings: {summary['warnings']}",
        "",
        "> This is a design-time assessment of the canonical model. It does not query Azure, Kubernetes, or deployed resources and is not proof of runtime compliance.",
        "",
    ]
    if not items:
        lines.extend(["No findings.", ""])
    else:
        lines.extend(["## Findings", "", "| Level | Gate | Code | Subject | Finding | Waiver |", "| --- | --- | --- | --- | --- | --- |"])
        order = {"blocker": 0, "warning": 1, "info": 2}
        for item in sorted(items, key=lambda value: (order.get(value.level, 9), value.gate, value.code, value.subject)):
            message = item.message.replace("|", "\\|").replace("\n", " ")
            subject = item.subject.replace("|", "\\|")
            waiver = item.waived_by or "—"
            lines.append(f"| {item.level} | {item.gate} | `{item.code}` | `{subject}` | {message} | {waiver} |")
        lines.extend(["", "## Remediation", ""])
        for item in sorted(items, key=lambda value: (order.get(value.level, 9), value.code, value.subject)):
            status = f" — waived by `{item.waived_by}`" if item.waived_by else ""
            lines.extend([f"### {item.code}: {item.subject}{status}", "", item.remediation, ""])
    return ("\n".join(lines).rstrip() + "\n").encode("utf-8")


def traceability_csv(model: dict[str, Any]) -> bytes:
    rows: list[list[str]] = []
    requirements = {item["id"]: item for item in model.get("requirements", []) if isinstance(item, dict) and item.get("id")}
    for collection_name in ("components", "relationships", "controls", "views"):
        for item in model.get(collection_name, []):
            if not isinstance(item, dict) or not item.get("id"):
                continue
            for requirement_id in item.get("requirements", []):
                requirement = requirements.get(requirement_id, {})
                rows.append(
                    [
                        requirement_id,
                        str(requirement.get("type", "")),
                        str(requirement.get("priority", "")),
                        str(requirement.get("status", "")),
                        str(requirement.get("text", "")),
                        collection_name[:-1] if collection_name.endswith("s") else collection_name,
                        str(item["id"]),
                        str(item.get("name") or item.get("title") or item.get("label") or ""),
                        str(item.get("owner", "")),
                    ]
                )
    ui_spec = model.get("ui_spec", {}) if isinstance(model.get("ui_spec"), dict) else {}
    for collection_name in ("screens", "flows", "components", "bindings", "navigation"):
        for item in ui_spec.get(collection_name, []):
            if not isinstance(item, dict) or not item.get("id"):
                continue
            for requirement_id in item.get("requirements", []):
                requirement = requirements.get(requirement_id, {})
                rows.append(
                    [
                        requirement_id,
                        str(requirement.get("type", "")),
                        str(requirement.get("priority", "")),
                        str(requirement.get("status", "")),
                        str(requirement.get("text", "")),
                        "ui_" + (collection_name[:-1] if collection_name.endswith("s") else collection_name),
                        str(item["id"]),
                        str(item.get("name") or item.get("operation") or item.get("trigger") or ""),
                        str(item.get("owner", "")),
                    ]
                )
    traced = {row[0] for row in rows}
    for requirement_id, requirement in requirements.items():
        if requirement_id not in traced:
            rows.append([requirement_id, str(requirement.get("type", "")), str(requirement.get("priority", "")), str(requirement.get("status", "")), str(requirement.get("text", "")), "", "", "UNTRACED", str(requirement.get("owner", ""))])
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(["requirement_id", "requirement_type", "priority", "requirement_status", "requirement", "element_type", "element_id", "element", "owner"])
    writer.writerows(sorted(rows, key=lambda row: (row[0], row[5], row[6])))
    return stream.getvalue().encode("utf-8")


def decisions_markdown(model: dict[str, Any]) -> bytes:
    project = model.get("project", {})
    lines = [f"# Architecture decisions: {project.get('title', project.get('id', 'Architecture'))}", ""]
    decisions = [item for item in model.get("decisions", []) if isinstance(item, dict)]
    if not decisions:
        lines.extend(["No architecture decisions recorded.", ""])
    for decision in decisions:
        lines.extend(
            [
                f"## {decision.get('id', 'decision')}: {decision.get('title', '')}",
                "",
                f"- Status: **{str(decision.get('status', '')).upper()}**",
                f"- Owner: {decision.get('owner', '')}",
                f"- Date: {decision.get('date', '')}",
                f"- Affected: {', '.join(f'`{item}`' for item in decision.get('affected', [])) or '—'}",
                "",
                "### Context",
                "",
                str(decision.get("context", "")),
                "",
                "### Decision",
                "",
                str(decision.get("choice", "")),
                "",
                "### Rationale",
                "",
                str(decision.get("rationale", "")),
                "",
                "### Alternatives considered",
                "",
            ]
        )
        lines.extend([f"- {item}" for item in decision.get("alternatives", [])] or ["- None recorded"])
        lines.extend(["", "### Consequences", ""])
        lines.extend([f"- {item}" for item in decision.get("consequences", [])] or ["- None recorded"])
        lines.append("")
    return ("\n".join(lines).rstrip() + "\n").encode("utf-8")


def risk_threat_markdown(model: dict[str, Any]) -> bytes:
    project = model.get("project", {})
    lines = [
        f"# Risk and threat summary: {project.get('title', project.get('id', 'Architecture'))}",
        "",
        "> This register is design evidence. Validate controls against implementation and authorized runtime evidence before production approval.",
        "",
    ]
    risks = [item for item in model.get("risks", []) if isinstance(item, dict)]
    if not risks:
        lines.extend(["No risks recorded.", ""])
    else:
        lines.extend(["| ID | Category | Exposure | Risk | Mitigation | Owner | Status |", "| --- | --- | --- | --- | --- | --- | --- |"])
        order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        for risk in sorted(risks, key=lambda item: (order.get(str(item.get("exposure")), 9), str(item.get("id")))):
            values = [
                f"`{risk.get('id', '')}`",
                str(risk.get("category", "")),
                str(risk.get("exposure", "")),
                str(risk.get("title", "")),
                str(risk.get("mitigation", "")),
                str(risk.get("owner", "")),
                str(risk.get("status", "")),
            ]
            lines.append("| " + " | ".join(value.replace("|", "\\|").replace("\n", " ") for value in values) + " |")
        lines.append("")

    controls = [item for item in model.get("controls", []) if isinstance(item, dict)]
    security_controls = [item for item in controls if str(item.get("domain", "")).lower() in {"security", "identity", "network", "data-protection", "supply-chain"}]
    lines.extend(["## Security control coverage", ""])
    if security_controls:
        for control in security_controls:
            lines.extend(
                [
                    f"- **{control.get('id', '')} · {control.get('name', '')}** — {control.get('implementation', '')} "
                    f"(owner: {control.get('owner', '')}; status: {control.get('status', '')})"
                ]
            )
    else:
        lines.append("- No security controls are recorded.")
    lines.extend(["", "## Threat-model prompts for implementation review", "", "- Entry points and trust crossings: validate authentication, authorization, abuse controls, TLS, rate limiting, and evidence.", "- Sensitive data: validate minimization, classification, access logging, retention, deletion, backup isolation, and key ownership.", "- Workload and platform identities: validate least privilege, token scope/lifetime, rotation, privileged escalation paths, and break-glass monitoring.", "- Supply chain: validate dependency and image provenance, SBOM, scanning, signing, promotion, admission, and rollback.", "- Failure and recovery: validate timeout, retry, idempotency, backpressure, DLQ/replay, failover, restore, and incident runbooks.", ""])
    return ("\n".join(lines).rstrip() + "\n").encode("utf-8")


def ui_specification_markdown(model: dict[str, Any]) -> bytes:
    project = model.get("project", {})
    ui = model.get("ui_spec", {}) if isinstance(model.get("ui_spec"), dict) else {}
    design_system = ui.get("design_system", {}) if isinstance(ui.get("design_system"), dict) else {}
    lines = [
        f"# UI specification: {project.get('title', project.get('id', 'Product'))}",
        "",
        f"- Status: **{str(ui.get('status', 'not-requested')).upper()}**",
        f"- Platforms: {', '.join(str(item) for item in ui.get('platforms', [])) or '—'}",
        f"- Design system: {design_system.get('name', '—')}",
        f"- Design source: {design_system.get('source', '—')}",
        f"- Reuse policy: {design_system.get('reuse_policy', '—')}",
        "",
        "> This is a design and implementation contract. Accessibility claims require testing against the implemented product, not only this specification.",
        "",
        "## Personas and access needs",
        "",
    ]
    for persona in ui.get("personas", []):
        if not isinstance(persona, dict):
            continue
        lines.extend(
            [
                f"### {persona.get('id', '')}: {persona.get('name', '')}",
                "",
                f"- Roles: {', '.join(str(item) for item in persona.get('roles', [])) or '—'}",
                f"- Goals: {', '.join(str(item) for item in persona.get('goals', [])) or '—'}",
                f"- Access needs: {', '.join(str(item) for item in persona.get('access_needs', [])) or '—'}",
                "",
            ]
        )
    lines.extend(["## Responsive contract", "", "| Breakpoint | Range | Grid | Gutter |", "| --- | --- | --- | --- |"])
    for breakpoint in ui.get("breakpoints", []):
        if not isinstance(breakpoint, dict):
            continue
        maximum = "∞" if breakpoint.get("max_width") is None else str(breakpoint.get("max_width"))
        lines.append(f"| `{breakpoint.get('id', '')}` · {breakpoint.get('label', '')} | {breakpoint.get('min_width', '')}–{maximum}px | {breakpoint.get('columns', '')} columns | {breakpoint.get('gutter', '')}px |")
    lines.extend(["", "## User flows", ""])
    for flow in ui.get("flows", []):
        if not isinstance(flow, dict):
            continue
        lines.extend(
            [
                f"### {flow.get('id', '')}: {flow.get('name', '')}",
                "",
                f"- Actor: `{flow.get('actor', '')}`",
                f"- Goal: {flow.get('goal', '')}",
                f"- Preconditions: {', '.join(str(item) for item in flow.get('preconditions', [])) or 'None'}",
                "",
                "| Step | Screen | User action | Observable outcome | Alternate |",
                "| --- | --- | --- | --- | --- |",
            ]
        )
        for index, step in enumerate(flow.get("steps", []), start=1):
            if not isinstance(step, dict):
                continue
            values = [str(index), f"`{step.get('screen', '')}`", str(step.get("action", "")), str(step.get("outcome", "")), str(step.get("alternate", "—"))]
            lines.append("| " + " | ".join(value.replace("|", "\\|").replace("\n", " ") for value in values) + " |")
        lines.extend(["", f"Success: {', '.join(str(item) for item in flow.get('outcomes', [])) or '—'}", "", f"Exceptions: {', '.join(str(item) for item in flow.get('exceptions', [])) or '—'}", ""])

    lines.extend(["## Screen contracts", ""])
    component_index = {item.get("id"): item for item in ui.get("components", []) if isinstance(item, dict) and item.get("id")}
    for screen in ui.get("screens", []):
        if not isinstance(screen, dict):
            continue
        lines.extend(
            [
                f"### {screen.get('id', '')}: {screen.get('name', '')}",
                "",
                f"- Route: `{screen.get('route', '')}`",
                f"- Purpose: {screen.get('purpose', '')}",
                f"- Roles: {', '.join(str(item) for item in screen.get('roles', [])) or '—'}",
                f"- Data classification: {screen.get('data_classification', '')}",
                f"- Requirements: {', '.join(f'`{item}`' for item in screen.get('requirements', [])) or '—'}",
                "",
                "#### Regions and actions",
                "",
                "| Region | Landmark/role | Component | Visibility | Actions | Bindings |",
                "| --- | --- | --- | --- | --- | --- |",
            ]
        )
        for region in screen.get("regions", []):
            if not isinstance(region, dict):
                continue
            component = component_index.get(region.get("component"), {})
            actions = ", ".join(f"{item.get('label', item.get('id', ''))} [{item.get('permission', '')}]" for item in region.get("actions", []) if isinstance(item, dict)) or "—"
            values = [f"`{region.get('id', '')}` · {region.get('name', '')}", str(region.get("role", "")), str(component.get("name", region.get("component", ""))), str(region.get("visible_when", "")), actions, ", ".join(f"`{item}`" for item in region.get("bindings", [])) or "—"]
            lines.append("| " + " | ".join(value.replace("|", "\\|").replace("\n", " ") for value in values) + " |")
        lines.extend(["", "#### States", "", "| State | Trigger | Content | Actions | Focus | Announcement |", "| --- | --- | --- | --- | --- | --- |"])
        for state in screen.get("states", []):
            if not isinstance(state, dict):
                continue
            values = [f"`{state.get('id', '')}` · {state.get('kind', '')}", str(state.get("trigger", "")), str(state.get("content", "")), ", ".join(f"`{item}`" for item in state.get("available_actions", [])) or "—", str(state.get("focus_target", "")), str(state.get("announcement", ""))]
            lines.append("| " + " | ".join(value.replace("|", "\\|").replace("\n", " ") for value in values) + " |")
        lines.extend(["", "#### Layout coverage", ""])
        for layout in screen.get("layouts", []):
            if isinstance(layout, dict):
                lines.append(f"- `{layout.get('breakpoint', '')}`: {layout.get('width', '')}×{layout.get('height', '')}; {len(layout.get('placements', []))} regions placed.")
        lines.append("")

    lines.extend(["## UI-to-system bindings", "", "| Binding | Screen / region | Architecture target | Operation | Authorization | Loading | Error |", "| --- | --- | --- | --- | --- | --- | --- |"])
    for binding in ui.get("bindings", []):
        if not isinstance(binding, dict):
            continue
        target = f"`{binding.get('architecture_component', '')}`" + (f" via `{binding.get('relationship')}`" if binding.get("relationship") else "")
        values = [f"`{binding.get('id', '')}`", f"`{binding.get('screen', '')}` / `{binding.get('region', '')}`", target, f"{binding.get('transport', '')} · {binding.get('operation', '')}", str(binding.get("authorization", "")), str(binding.get("loading", "")), str(binding.get("error", ""))]
        lines.append("| " + " | ".join(value.replace("|", "\\|").replace("\n", " ") for value in values) + " |")

    accessibility = ui.get("accessibility", {}) if isinstance(ui.get("accessibility"), dict) else {}
    implementation = ui.get("implementation", {}) if isinstance(ui.get("implementation"), dict) else {}
    lines.extend(["", "## Accessibility contract", ""])
    for key in ("target", "keyboard", "focus", "screen_reader", "contrast", "zoom_reflow", "reduced_motion"):
        lines.append(f"- **{key.replace('_', ' ').title()}:** {accessibility.get(key, '—')}")
    lines.extend(["", "Verification:", ""])
    lines.extend([f"- {item}" for item in accessibility.get("testing", [])] or ["- Not defined"])
    lines.extend(["", "## Implementation handoff", ""])
    for key in ("front_end", "design_system_package", "state_management", "data_fetching", "validation", "testing", "feature_flags", "observability"):
        lines.append(f"- **{key.replace('_', ' ').title()}:** {implementation.get(key, '—')}")
    lines.append("")
    return ("\n".join(lines).rstrip() + "\n").encode("utf-8")


def ui_component_matrix_csv(model: dict[str, Any]) -> bytes:
    ui = model.get("ui_spec", {}) if isinstance(model.get("ui_spec"), dict) else {}
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(["component_id", "name", "category", "description", "variants", "states", "props", "events", "accessibility", "implementation", "requirements"])
    for component in ui.get("components", []):
        if not isinstance(component, dict):
            continue
        writer.writerow(
            [
                component.get("id", ""), component.get("name", ""), component.get("category", ""), component.get("description", ""),
                " | ".join(str(item) for item in component.get("variants", [])), " | ".join(str(item) for item in component.get("states", [])),
                " | ".join(str(item) for item in component.get("props", [])), " | ".join(str(item) for item in component.get("events", [])),
                component.get("accessibility", ""), component.get("implementation", ""), " | ".join(str(item) for item in component.get("requirements", [])),
            ]
        )
    return stream.getvalue().encode("utf-8")


def ui_acceptance_markdown(model: dict[str, Any]) -> bytes:
    project = model.get("project", {})
    ui = model.get("ui_spec", {}) if isinstance(model.get("ui_spec"), dict) else {}
    lines = [
        f"# UI acceptance plan: {project.get('title', project.get('id', 'Product'))}",
        "",
        "> Execute these scenarios against the implemented UI at every supported breakpoint. A generated plan is not test evidence.",
        "",
        "## Goal-level journeys",
        "",
    ]
    for flow in ui.get("flows", []):
        if not isinstance(flow, dict):
            continue
        lines.extend([f"### `{flow.get('id', '')}` · {flow.get('name', '')}", "", f"**Given** {'; '.join(str(item) for item in flow.get('preconditions', [])) or 'the declared persona and authorization context'}", ""])
        for index, step in enumerate(flow.get("steps", []), start=1):
            if isinstance(step, dict):
                keyword = "When" if index == 1 else "And"
                lines.append(f"**{keyword}** on `{step.get('screen', '')}` the user {str(step.get('action', '')).rstrip('.')}")
                lines.append(f"**Then** {str(step.get('outcome', '')).rstrip('.')}")
                if step.get("alternate"):
                    lines.append(f"**And when the exception occurs:** {step.get('alternate')}")
                lines.append("")
        lines.extend(["Expected goal outcomes:", ""])
        lines.extend([f"- {item}" for item in flow.get("outcomes", [])] or ["- Not defined"])
        lines.extend(["", "Exception coverage:", ""])
        lines.extend([f"- {item}" for item in flow.get("exceptions", [])] or ["- No exceptions recorded"])
        lines.append("")

    lines.extend(["## Screen-state contract tests", ""])
    for screen in ui.get("screens", []):
        if not isinstance(screen, dict):
            continue
        lines.extend([f"### `{screen.get('id', '')}` · {screen.get('name', '')}", ""])
        for state in screen.get("states", []):
            if not isinstance(state, dict):
                continue
            lines.extend(
                [
                    f"- [ ] `{state.get('kind', '')}` / `{state.get('id', '')}`: when {state.get('trigger', '')}, show “{state.get('content', '')}”; expose only {', '.join(str(item) for item in state.get('available_actions', [])) or 'no actions'}; move focus to {state.get('focus_target', '')}; announce “{state.get('announcement', '')}”.",
                ]
            )
        for layout in screen.get("layouts", []):
            if isinstance(layout, dict):
                lines.append(f"- [ ] `{layout.get('breakpoint', '')}`: all {len(layout.get('placements', []))} regions render without overlap, clipping, horizontal page scroll, or lost action access.")
        lines.append("")

    lines.extend(["## UI-to-system contract tests", ""])
    for binding in ui.get("bindings", []):
        if not isinstance(binding, dict):
            continue
        lines.extend(
            [
                f"### `{binding.get('id', '')}` · {binding.get('operation', '')}",
                "",
                f"- [ ] Request contract: {binding.get('request', '')}",
                f"- [ ] Response contract: {binding.get('response', '')}",
                f"- [ ] Authorization: {binding.get('authorization', '')}",
                f"- [ ] Loading behavior: {binding.get('loading', '')}",
                f"- [ ] Error behavior: {binding.get('error', '')}",
                f"- [ ] Architecture trace: `{binding.get('architecture_component', '')}`" + (f" / `{binding.get('relationship')}`" if binding.get("relationship") else ""),
                "",
            ]
        )

    accessibility = ui.get("accessibility", {}) if isinstance(ui.get("accessibility"), dict) else {}
    lines.extend(["## Accessibility and quality gates", "", f"Target: **{accessibility.get('target', 'Not defined')}**", ""])
    for item in accessibility.get("testing", []):
        lines.append(f"- [ ] {item}")
    lines.extend(
        [
            "- [ ] Keyboard order and visible focus match the documented landmarks, actions, dialogs, and recovery path.",
            "- [ ] Screen-reader names, roles, values, instructions, errors, live announcements, and page titles match the state contract.",
            "- [ ] Text and non-text contrast, target size, zoom/reflow, orientation, and text spacing pass at supported breakpoints.",
            "- [ ] Authentication does not depend on a cognitive-function test; repeated data entry and accessible authentication requirements are verified.",
            "- [ ] Automated accessibility, component, integration, end-to-end, and visual-regression suites run in CI with owned failure thresholds.",
            "- [ ] No animation is introduced; state changes remain understandable without motion.",
            "",
        ]
    )
    return ("\n".join(lines).rstrip() + "\n").encode("utf-8")


def design_tokens_json(model: dict[str, Any]) -> bytes:
    ui = model.get("ui_spec", {}) if isinstance(model.get("ui_spec"), dict) else {}
    design_system = ui.get("design_system", {}) if isinstance(ui.get("design_system"), dict) else {}
    payload = {
        "$schema": "https://design-tokens.github.io/community-group/format/",
        "project_id": model.get("project", {}).get("id"),
        "design_system": design_system.get("name"),
        "source": design_system.get("source"),
        "tokens": design_system.get("tokens", {}),
        "motion": {"enabled": False, "contract": "Static state changes only; no animation."},
    }
    return (json.dumps(payload, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def semantic_diff(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {
        "schema_version": "1.0",
        "before": {"project_id": before.get("project", {}).get("id"), "version": before.get("project", {}).get("version"), "sha256": model_digest(before)},
        "after": {"project_id": after.get("project", {}).get("id"), "version": after.get("project", {}).get("version"), "sha256": model_digest(after)},
        "collections": {},
    }
    sources: list[tuple[str, list[Any], list[Any]]] = [
        (name, before.get(name, []), after.get(name, []))
        for name in ("requirements", "controls", "components", "relationships", "views", "decisions", "risks", "assumptions", "open_questions", "waivers")
    ]
    before_ui = before.get("ui_spec", {}) if isinstance(before.get("ui_spec"), dict) else {}
    after_ui = after.get("ui_spec", {}) if isinstance(after.get("ui_spec"), dict) else {}
    sources.extend((f"ui_{name}", before_ui.get(name, []), after_ui.get(name, [])) for name in ("personas", "breakpoints", "flows", "screens", "components", "bindings", "navigation", "analytics"))
    sources.append(
        (
            "ui_contracts",
            [{"id": "ui-design-system", **before_ui.get("design_system", {})}, {"id": "ui-accessibility", **before_ui.get("accessibility", {})}, {"id": "ui-implementation", **before_ui.get("implementation", {})}],
            [{"id": "ui-design-system", **after_ui.get("design_system", {})}, {"id": "ui-accessibility", **after_ui.get("accessibility", {})}, {"id": "ui-implementation", **after_ui.get("implementation", {})}],
        )
    )
    for name, before_items, after_items in sources:
        before_index = {item.get("id"): item for item in before_items if isinstance(item, dict) and item.get("id")}
        after_index = {item.get("id"): item for item in after_items if isinstance(item, dict) and item.get("id")}
        added = sorted(set(after_index) - set(before_index))
        removed = sorted(set(before_index) - set(after_index))
        changed = []
        moved_only = []
        for entity_id in sorted(set(before_index) & set(after_index)):
            if before_index[entity_id] == after_index[entity_id]:
                continue
            if name == "views" and _without_placement(before_index[entity_id]) == _without_placement(after_index[entity_id]):
                moved_only.append(entity_id)
            elif name == "ui_screens" and _without_ui_placement(before_index[entity_id]) == _without_ui_placement(after_index[entity_id]):
                moved_only.append(entity_id)
            else:
                changed.append({"id": entity_id, "fields": _changed_fields(before_index[entity_id], after_index[entity_id])})
        result["collections"][name] = {"added": added, "removed": removed, "changed": changed, "moved_only": moved_only}
    return result


def _without_placement(view: dict[str, Any]) -> dict[str, Any]:
    clone = json.loads(json.dumps(view))
    for node in clone.get("nodes", []):
        for key in ("x", "y", "w", "h"):
            node.pop(key, None)
    for boundary in clone.get("boundaries", []):
        for key in ("x", "y", "w", "h"):
            boundary.pop(key, None)
    legend = clone.get("legend", {})
    for key in ("x", "y"):
        legend.pop(key, None)
    return clone


def _without_ui_placement(screen: dict[str, Any]) -> dict[str, Any]:
    clone = json.loads(json.dumps(screen))
    for layout in clone.get("layouts", []):
        for placement in layout.get("placements", []):
            for key in ("x", "y", "w", "h"):
                placement.pop(key, None)
    return clone


def _changed_fields(before: dict[str, Any], after: dict[str, Any]) -> list[str]:
    return sorted(key for key in set(before) | set(after) if before.get(key) != after.get(key))


def diff_markdown(diff: dict[str, Any]) -> bytes:
    lines = [
        "# Architecture semantic delta",
        "",
        f"- Before: `{diff['before'].get('project_id')}` v`{diff['before'].get('version')}` · `{diff['before'].get('sha256')}`",
        f"- After: `{diff['after'].get('project_id')}` v`{diff['after'].get('version')}` · `{diff['after'].get('sha256')}`",
        "",
        "> Geometry-only movement is reported separately and is not treated as an architecture semantic change.",
        "",
    ]
    any_change = False
    for name, delta in diff.get("collections", {}).items():
        if not any(delta.get(key) for key in ("added", "removed", "changed", "moved_only")):
            continue
        any_change = True
        lines.extend([f"## {name.replace('_', ' ').title()}", ""])
        if delta.get("added"):
            lines.append("- Added: " + ", ".join(f"`{item}`" for item in delta["added"]))
        if delta.get("removed"):
            lines.append("- Removed: " + ", ".join(f"`{item}`" for item in delta["removed"]))
        for item in delta.get("changed", []):
            lines.append(f"- Changed `{item['id']}`: {', '.join(f'`{field}`' for field in item.get('fields', []))}")
        if delta.get("moved_only"):
            lines.append("- Geometry only: " + ", ".join(f"`{item}`" for item in delta["moved_only"]))
        lines.append("")
    if not any_change:
        lines.extend(["No semantic or geometry changes.", ""])
    return ("\n".join(lines).rstrip() + "\n").encode("utf-8")


def receipt_payload(model: dict[str, Any], artifacts: list[dict[str, Any]], summary: dict[str, Any], generator_version: str) -> bytes:
    ui_active = isinstance(model.get("ui_spec"), dict) and model["ui_spec"].get("status") != "not-requested"
    payload = {
        "schema_version": "1.0",
        "generator": {"name": "arch-studio", "version": generator_version},
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "project_id": model.get("project", {}).get("id"),
        "project_version": model.get("project", {}).get("version"),
        "model_sha256": model_digest(model),
        "gate": summary,
        "artifacts": artifacts,
        "claims": {
            "drawio": "Multi-page uncompressed mxGraph XML parsed successfully.",
            "review_html": "Self-contained static review workspace; no animation or external runtime dependency.",
            "governance": "Design-time model assessment only; not live compliance evidence.",
            **({"ui_spec": "Responsive UI, state, binding, accessibility, and acceptance artifacts derived from the same canonical model; not implementation conformance evidence."} if ui_active else {}),
        },
    }
    return (json.dumps(payload, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
