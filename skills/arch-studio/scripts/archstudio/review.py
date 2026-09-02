from __future__ import annotations

import html
import json
import math
from typing import Any

from .drawio import BOUNDARY_STYLES, EDGE_STYLES, KIND_STYLES


def _esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def _json_for_script(value: Any) -> str:
    return (
        json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


def _wrap(text: str, limit: int = 23, max_lines: int = 3) -> list[str]:
    words = str(text).split()
    if not words:
        return [""]
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        if len(current) + len(word) + 1 <= limit:
            current += " " + word
        else:
            lines.append(current)
            current = word
            if len(lines) == max_lines - 1:
                break
    remaining_start = len(" ".join(lines + [current]).split())
    remaining_words = words[remaining_start:]
    if remaining_words:
        current += " " + " ".join(remaining_words)
    if len(current) > limit + 8:
        current = current[: limit + 5].rstrip() + "…"
    lines.append(current)
    return lines[:max_lines]


def _component_badge(component: dict[str, Any]) -> str:
    if component.get("azure_service"):
        parts = str(component.get("technology", component.get("name", "AZ"))).replace("Azure", "").split()
        letters = "".join(part[0] for part in parts if part and part[0].isalnum())[:3].upper()
        return letters or "AZ"
    mapping = {
        "actor": "USR",
        "external-system": "EXT",
        "client": "UI",
        "gateway": "GW",
        "service": "SVC",
        "function": "FN",
        "worker": "WK",
        "message-broker": "MSG",
        "database": "DB",
        "cache": "C",
        "storage": "ST",
        "identity": "ID",
        "security": "SEC",
        "observability": "OBS",
        "pipeline": "CD",
        "repository": "GIT",
        "kubernetes": "K8S",
        "network": "NET",
    }
    return mapping.get(str(component.get("kind")), "CMP")


def _node_svg(component: dict[str, Any], placement: dict[str, Any]) -> str:
    component_id = component["id"]
    x, y = float(placement["x"]), float(placement["y"])
    w, h = float(placement["w"]), float(placement["h"])
    colors = KIND_STYLES.get(component.get("kind", "generic"), KIND_STYLES["generic"])
    lines = _wrap(str(component.get("name", component_id)), max(16, int(w / 8)))
    technology = str(component.get("technology", ""))
    line_height = 17
    content_height = len(lines) * line_height + (14 if technology else 0)
    start_y = y + (h - content_height) / 2 + 6
    text = []
    for index, line in enumerate(lines):
        text.append(f'<tspan x="{x + w / 2:.1f}" y="{start_y + index * line_height:.1f}">{_esc(line)}</tspan>')
    if technology:
        tech = technology if len(technology) <= 28 else technology[:25] + "…"
        text.append(f'<tspan class="node-tech" x="{x + w / 2:.1f}" y="{start_y + len(lines) * line_height + 1:.1f}">{_esc(tech)}</tspan>')
    lifecycle = component.get("lifecycle")
    lifecycle_badge = ""
    if lifecycle in {"new", "changed", "retiring"}:
        lifecycle_badge = f'<text class="lifecycle lifecycle-{_esc(lifecycle)}" x="{x + w - 8:.1f}" y="{y + 15:.1f}" text-anchor="end">{_esc(str(lifecycle).upper())}</text>'
    badge = _component_badge(component)
    return (
        f'<g class="diagram-object component kind-{_esc(component.get("kind", "generic"))}" '
        f'data-review-id="component:{_esc(component_id)}" tabindex="0" role="button" aria-label="Review {_esc(component.get("name", component_id))}">'
        f'<title>{_esc(component.get("description", ""))}</title>'
        f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="12" fill="{colors["fill"]}" stroke="{colors["stroke"]}" stroke-width="2"/>'
        f'<circle cx="{x + 22:.1f}" cy="{y + 22:.1f}" r="14" fill="{colors["stroke"]}"/>'
        f'<text class="node-badge" x="{x + 22:.1f}" y="{y + 26:.1f}" text-anchor="middle">{_esc(badge)}</text>'
        f'{lifecycle_badge}'
        f'<text class="node-label" fill="{colors["font"]}" text-anchor="middle">{"".join(text)}</text>'
        f'<circle class="review-dot" data-dot-for="component:{_esc(component_id)}" cx="{x + w - 11:.1f}" cy="{y + h - 11:.1f}" r="5"/>'
        "</g>"
    )


def _edge_points(source: dict[str, Any], target: dict[str, Any]) -> tuple[str, float, float]:
    sx = float(source["x"]) + float(source["w"]) / 2
    sy = float(source["y"]) + float(source["h"]) / 2
    tx = float(target["x"]) + float(target["w"]) / 2
    ty = float(target["y"]) + float(target["h"]) / 2
    dx, dy = tx - sx, ty - sy
    if abs(dx) >= abs(dy):
        sx = float(source["x"]) + (float(source["w"]) if dx >= 0 else 0)
        tx = float(target["x"]) + (0 if dx >= 0 else float(target["w"]))
        mid = (sx + tx) / 2
        path = f"M {sx:.1f} {sy:.1f} H {mid:.1f} V {ty:.1f} H {tx:.1f}"
        lx, ly = mid, (sy + ty) / 2
    else:
        sy = float(source["y"]) + (float(source["h"]) if dy >= 0 else 0)
        ty = float(target["y"]) + (0 if dy >= 0 else float(target["h"]))
        mid = (sy + ty) / 2
        path = f"M {sx:.1f} {sy:.1f} V {mid:.1f} H {tx:.1f} V {ty:.1f}"
        lx, ly = (sx + tx) / 2, mid
    return path, lx, ly


def _edge_svg(relationship: dict[str, Any], placements: dict[str, dict[str, Any]], marker_prefix: str) -> str:
    source = placements.get(relationship.get("from"))
    target = placements.get(relationship.get("to"))
    if not source or not target:
        return ""
    mode = str(relationship.get("mode", "sync"))
    style = EDGE_STYLES.get(mode, EDGE_STYLES["sync"])
    path, lx, ly = _edge_points(source, target)
    label = str(relationship.get("label", ""))
    technical = " · ".join(
        item
        for item in (
            str(relationship.get("protocol", "")) + (f"/{relationship.get('port')}" if relationship.get("port") not in (None, "") else ""),
            str(relationship.get("auth", "")),
            mode,
        )
        if item
    )
    label_width = min(330.0, max(110.0, len(label) * 6.1 + 22.0))
    dash = "7 5" if style["dash"] == "1" else "none"
    relationship_id = relationship["id"]
    return (
        f'<g class="diagram-object relationship mode-{_esc(mode)}" data-review-id="relationship:{_esc(relationship_id)}" tabindex="0" role="button" aria-label="Review connection {_esc(label)}">'
        f'<path class="edge-hit" d="{path}"/>'
        f'<path class="edge-line" d="{path}" stroke="{style["stroke"]}" stroke-dasharray="{dash}" marker-end="url(#{marker_prefix}-{_esc(mode)})"/>'
        f'<rect class="edge-label-bg" x="{lx - label_width / 2:.1f}" y="{ly - 22:.1f}" width="{label_width:.1f}" height="38" rx="7"/>'
        f'<text class="edge-label" x="{lx:.1f}" y="{ly - 7:.1f}" text-anchor="middle">{_esc(label if len(label) <= 48 else label[:45] + "…")}</text>'
        f'<text class="edge-tech" x="{lx:.1f}" y="{ly + 8:.1f}" text-anchor="middle">{_esc(technical)}</text>'
        f'<circle class="review-dot" data-dot-for="relationship:{_esc(relationship_id)}" cx="{lx + label_width / 2 - 8:.1f}" cy="{ly + 9:.1f}" r="5"/>'
        "</g>"
    )


def _boundary_svg(boundary: dict[str, Any]) -> str:
    x, y = float(boundary["x"]), float(boundary["y"])
    w, h = float(boundary["w"]), float(boundary["h"])
    fill, stroke = BOUNDARY_STYLES.get(str(boundary.get("kind", "generic")), BOUNDARY_STYLES["generic"])
    dash = "8 6" if boundary.get("kind") in {"trust", "data-residency", "failure-domain"} else "none"
    return (
        f'<g class="boundary boundary-{_esc(boundary.get("kind", "generic"))}">'
        f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="14" fill="{fill}" fill-opacity="0.40" stroke="{stroke}" stroke-width="1.8" stroke-dasharray="{dash}"/>'
        f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="30" rx="14" fill="{fill}" stroke="none"/>'
        f'<text class="boundary-label" x="{x + 12:.1f}" y="{y + 20:.1f}">{_esc(boundary.get("label", boundary.get("id", "Boundary")))}</text>'
        "</g>"
    )


def _legend_svg(view: dict[str, Any], component_index: dict[str, dict[str, Any]], relationship_index: dict[str, dict[str, Any]]) -> str:
    legend = view.get("legend", {})
    if not isinstance(legend, dict) or legend.get("mode") == "hidden":
        return ""
    entries: list[tuple[str, str]] = []
    if legend.get("mode") == "authored":
        for entry in legend.get("entries", []):
            if isinstance(entry, dict):
                entries.append((str(entry.get("label", "Symbol")), str(entry.get("color", "#667085"))))
    else:
        if view.get("type") == "ui-wireframe":
            entries = [("Primary/data region", "#2E90FA"), ("Action region", "#12B76A"), ("Navigation landmark", "#7A5AF8"), ("Rendered state", "#F79009")]
        elif view.get("type") == "user-flow":
            entries = [("Persona", "#4F6BED"), ("Screen step", "#2E90FA"), ("Exception path", "#B54708")]
        elif view.get("type") == "ui-state-map":
            entries = [("Screen state", "#7A5AF8"), ("Focus and announcement", "#2E90FA")]
        kinds: list[str] = []
        if view.get("type") not in {"ui-wireframe", "user-flow", "ui-state-map"}:
            for placement in view.get("nodes", []):
                component = component_index.get(placement.get("component"), {}) if isinstance(placement, dict) else {}
                kind = str(component.get("kind", "generic"))
                if kind not in kinds:
                    kinds.append(kind)
            for kind in kinds[:6]:
                entries.append((kind.replace("-", " ").title(), KIND_STYLES.get(kind, KIND_STYLES["generic"])["stroke"]))
            modes: list[str] = []
            for edge_id in view.get("edges", []):
                mode = str(relationship_index.get(edge_id, {}).get("mode", "sync"))
                if mode not in modes:
                    modes.append(mode)
            for mode in modes[:4]:
                entries.append((f"{mode.title()} flow", EDGE_STYLES.get(mode, EDGE_STYLES["sync"])["stroke"]))
            if view.get("type") == "sequence":
                entries = [("Synchronous", EDGE_STYLES["sync"]["stroke"]), ("Async or return", EDGE_STYLES["async"]["stroke"])]
    if not entries:
        return ""
    w, row_h = 250.0, 24.0
    h = 36 + len(entries) * row_h
    x = float(legend.get("x", float(view.get("width", 1600)) - w - 24))
    y = float(legend.get("y", float(view.get("height", 900)) - h - 24))
    rows = []
    for index, (label, color) in enumerate(entries):
        row_y = y + 36 + index * row_h
        rows.append(f'<rect x="{x + 12:.1f}" y="{row_y - 10:.1f}" width="12" height="12" rx="3" fill="{_esc(color)}"/><text class="legend-item" x="{x + 32:.1f}" y="{row_y:.1f}">{_esc(label)}</text>')
    return f'<g class="legend"><rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="10"/><text class="legend-title" x="{x + 12:.1f}" y="{y + 22:.1f}">Legend</text>{"".join(rows)}</g>'


def _graph_svg(view: dict[str, Any], components: dict[str, dict[str, Any]], relationships: dict[str, dict[str, Any]]) -> str:
    width, height = float(view.get("width", 1600)), float(view.get("height", 900))
    placements = {item["component"]: item for item in view.get("nodes", []) if isinstance(item, dict) and item.get("component") in components}
    marker_prefix = f"arrow-{_esc(view['id'])}"
    defs = []
    for mode, style in EDGE_STYLES.items():
        defs.append(
            f'<marker id="{marker_prefix}-{_esc(mode)}" markerWidth="10" markerHeight="8" refX="9" refY="4" orient="auto" markerUnits="strokeWidth"><path d="M0,0 L10,4 L0,8 z" fill="{style["stroke"]}"/></marker>'
        )
    boundaries = "".join(_boundary_svg(item) for item in view.get("boundaries", []) if isinstance(item, dict))
    edges = "".join(_edge_svg(relationships[item], placements, marker_prefix) for item in view.get("edges", []) if item in relationships)
    nodes = "".join(_node_svg(components[item["component"]], item) for item in view.get("nodes", []) if isinstance(item, dict) and item.get("component") in components)
    legend = _legend_svg(view, components, relationships)
    return (
        f'<svg class="architecture-svg" data-view-id="{_esc(view["id"])}" viewBox="0 0 {width:.0f} {height:.0f}" role="img" aria-label="{_esc(view.get("title", view["id"]))}">'
        f'<defs>{"".join(defs)}</defs>'
        f'<rect class="canvas-bg" width="{width:.0f}" height="{height:.0f}" rx="16"/>'
        f'{boundaries}{edges}{nodes}{legend}'
        "</svg>"
    )


def _sequence_svg(view: dict[str, Any], components: dict[str, dict[str, Any]], relationships: dict[str, dict[str, Any]]) -> str:
    width, height = float(view.get("width", 1600)), float(view.get("height", 900))
    participants = [item for item in view.get("participants", []) if item in components]
    margin = 100.0
    step = (width - margin * 2) / max(1, len(participants) - 1)
    x_positions = {component_id: margin + index * step for index, component_id in enumerate(participants)}
    marker_prefix = f"arrow-{_esc(view['id'])}"
    defs = []
    for mode, style in EDGE_STYLES.items():
        defs.append(f'<marker id="{marker_prefix}-{_esc(mode)}" markerWidth="10" markerHeight="8" refX="9" refY="4" orient="auto" markerUnits="strokeWidth"><path d="M0,0 L10,4 L0,8 z" fill="{style["stroke"]}"/></marker>')
    headers: list[str] = []
    for component_id in participants:
        component = components[component_id]
        colors = KIND_STYLES.get(component.get("kind", "generic"), KIND_STYLES["generic"])
        x = x_positions[component_id]
        headers.append(
            f'<g class="diagram-object component" data-review-id="component:{_esc(component_id)}" tabindex="0" role="button">'
            f'<rect x="{x - 76:.1f}" y="92" width="152" height="62" rx="10" fill="{colors["fill"]}" stroke="{colors["stroke"]}" stroke-width="2"/>'
            f'<text class="sequence-participant" x="{x:.1f}" y="121" text-anchor="middle">{_esc(component.get("name", component_id))}</text>'
            f'<text class="sequence-tech" x="{x:.1f}" y="139" text-anchor="middle">{_esc(component.get("technology", ""))}</text>'
            f'<line class="lifeline" x1="{x:.1f}" y1="154" x2="{x:.1f}" y2="{height - 60:.1f}"/>'
            f'<circle class="review-dot" data-dot-for="component:{_esc(component_id)}" cx="{x + 63:.1f}" cy="143" r="5"/>'
            "</g>"
        )
    interactions: list[str] = []
    row_gap = max(38.0, min(60.0, (height - 300.0) / max(1, len(view.get("interactions", [])))))
    for index, interaction in enumerate(view.get("interactions", []), start=1):
        if not isinstance(interaction, dict) or interaction.get("from") not in x_positions or interaction.get("to") not in x_positions:
            continue
        sx, tx = x_positions[interaction["from"]], x_positions[interaction["to"]]
        y = 205 + (index - 1) * row_gap
        kind = str(interaction.get("kind", "sync"))
        style = EDGE_STYLES.get(kind, EDGE_STYLES["sync"])
        dash = "7 5" if style["dash"] == "1" else "none"
        interaction_id = str(interaction.get("id", f"interaction-{index}"))
        label = f"{index}. {interaction.get('label', '')}"
        label_x = (sx + tx) / 2
        interactions.append(
            f'<g class="diagram-object interaction" data-review-id="interaction:{_esc(interaction_id)}" tabindex="0" role="button">'
            f'<line class="edge-hit" x1="{sx:.1f}" y1="{y:.1f}" x2="{tx:.1f}" y2="{y:.1f}"/>'
            f'<line class="sequence-message" x1="{sx:.1f}" y1="{y:.1f}" x2="{tx:.1f}" y2="{y:.1f}" stroke="{style["stroke"]}" stroke-dasharray="{dash}" marker-end="url(#{marker_prefix}-{_esc(kind)})"/>'
            f'<rect class="edge-label-bg" x="{label_x - 125:.1f}" y="{y - 29:.1f}" width="250" height="22" rx="6"/>'
            f'<text class="edge-label" x="{label_x:.1f}" y="{y - 14:.1f}" text-anchor="middle">{_esc(label if len(label) <= 50 else label[:47] + "…")}</text>'
            f'<circle class="review-dot" data-dot-for="interaction:{_esc(interaction_id)}" cx="{label_x + 116:.1f}" cy="{y - 18:.1f}" r="5"/>'
            "</g>"
        )
    legend = _legend_svg(view, components, relationships)
    return (
        f'<svg class="architecture-svg" data-view-id="{_esc(view["id"])}" viewBox="0 0 {width:.0f} {height:.0f}" role="img" aria-label="{_esc(view.get("title", view["id"]))}">'
        f'<defs>{"".join(defs)}</defs><rect class="canvas-bg" width="{width:.0f}" height="{height:.0f}" rx="16"/>'
        f'{"".join(headers)}{"".join(interactions)}{legend}</svg>'
    )


def _ui_indexes(ui_spec: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]], dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    screens = {item["id"]: item for item in ui_spec.get("screens", []) if isinstance(item, dict) and item.get("id")}
    components = {item["id"]: item for item in ui_spec.get("components", []) if isinstance(item, dict) and item.get("id")}
    flows = {item["id"]: item for item in ui_spec.get("flows", []) if isinstance(item, dict) and item.get("id")}
    personas = {item["id"]: item for item in ui_spec.get("personas", []) if isinstance(item, dict) and item.get("id")}
    return screens, components, flows, personas


def _ui_wireframe_svg(view: dict[str, Any], ui_spec: dict[str, Any]) -> str:
    screens, components, _flows, _personas = _ui_indexes(ui_spec)
    screen = screens.get(view.get("screen"), {})
    layout = next((item for item in screen.get("layouts", []) if isinstance(item, dict) and item.get("breakpoint") == view.get("breakpoint")), {})
    regions = {item["id"]: item for item in screen.get("regions", []) if isinstance(item, dict) and item.get("id")}
    states = {item["id"]: item for item in screen.get("states", []) if isinstance(item, dict) and item.get("id")}
    state = states.get(view.get("state")) or next((item for item in states.values() if item.get("kind") == "default"), {})
    width, height = float(view.get("width", 1600)), float(view.get("height", 900))
    source_width = max(240.0, float(layout.get("width", 1280)))
    source_height = max(320.0, float(layout.get("height", 720)))
    scale = min(max(400.0, width - 380.0) / source_width, max(300.0, height - 150.0) / source_height)
    frame_width, frame_height = source_width * scale, source_height * scale
    ox, oy, chrome = 34.0, 74.0, 34.0
    screen_id = str(screen.get("id", "screen"))
    parts = [
        f'<g class="diagram-object ui-screen" data-review-id="ui-screen:{_esc(screen_id)}" tabindex="0" role="button">',
        f'<rect x="{ox:.1f}" y="{oy:.1f}" width="{frame_width:.1f}" height="{frame_height + chrome:.1f}" rx="12" fill="#FFFFFF" stroke="#667085" stroke-width="2"/>',
        f'<rect x="{ox:.1f}" y="{oy:.1f}" width="{frame_width:.1f}" height="{chrome:.1f}" rx="12" fill="#F2F4F7" stroke="#667085"/>',
        f'<text class="ui-chrome" x="{ox + 12:.1f}" y="{oy + 22:.1f}">●  ●  ●   {_esc(screen.get("route", "/"))} · {_esc(view.get("breakpoint", ""))}</text>',
        f'<circle class="review-dot" data-dot-for="ui-screen:{_esc(screen_id)}" cx="{ox + frame_width - 12:.1f}" cy="{oy + 17:.1f}" r="5"/>',
        '</g>',
    ]
    for placement in layout.get("placements", []):
        if not isinstance(placement, dict):
            continue
        region_id = placement.get("region")
        region = regions.get(region_id)
        if not region:
            continue
        component = components.get(region.get("component"), {})
        x = ox + float(placement.get("x", 0)) * scale
        y = oy + chrome + float(placement.get("y", 0)) * scale
        w = float(placement.get("w", 80)) * scale
        h = float(placement.get("h", 50)) * scale
        role = str(region.get("role", "region")).lower()
        fill, stroke = "#F9FAFB", "#98A2B3"
        if role in {"main", "form", "article"}:
            fill, stroke = "#EFF8FF", "#2E90FA"
        elif role in {"navigation", "banner", "complementary"}:
            fill, stroke = "#F4F3FF", "#7A5AF8"
        elif region.get("actions"):
            fill, stroke = "#ECFDF3", "#12B76A"
        review_id = f"ui-region:{screen_id}.{region_id}"
        description = str(region.get("description", ""))
        description = description if len(description) <= 72 else description[:69] + "…"
        parts.extend(
            [
                f'<g class="diagram-object ui-region" data-review-id="{_esc(review_id)}" tabindex="0" role="button" aria-label="Review {_esc(region.get("name", region_id))}">',
                f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="8" fill="{fill}" stroke="{stroke}" stroke-width="1.7"/>',
                f'<text class="ui-region-title" x="{x + 9:.1f}" y="{y + 19:.1f}">{_esc(region.get("name", region_id))}</text>',
                f'<text class="ui-region-meta" x="{x + 9:.1f}" y="{y + 35:.1f}">{_esc(component.get("name", region.get("component", "")))} · {_esc(region.get("role", ""))}</text>',
                f'<text class="ui-region-copy" x="{x + 9:.1f}" y="{y + 52:.1f}">{_esc(description)}</text>',
                f'<circle class="review-dot" data-dot-for="{_esc(review_id)}" cx="{x + w - 10:.1f}" cy="{y + 11:.1f}" r="5"/>',
                '</g>',
            ]
        )
        pill_x = x + 9.0
        pill_y = y + h - 25.0
        for action in [item for item in region.get("actions", []) if isinstance(item, dict)][:3]:
            label = str(action.get("label", action.get("id", "Action")))
            pill_w = min(max(66.0, len(label) * 6.0 + 18.0), max(66.0, w - 18.0))
            action_review = f"ui-action:{screen_id}.{action.get('id', 'action')}"
            parts.append(
                f'<g class="diagram-object ui-action" data-review-id="{_esc(action_review)}" tabindex="0" role="button">'
                f'<rect x="{pill_x:.1f}" y="{pill_y:.1f}" width="{pill_w:.1f}" height="20" rx="10" fill="#FFFFFF" stroke="{stroke}"/>'
                f'<text class="ui-action-label" x="{pill_x + pill_w / 2:.1f}" y="{pill_y + 14:.1f}" text-anchor="middle">{_esc(label)}</text>'
                f'</g>'
            )
            pill_x += pill_w + 7.0
            if pill_x + 66 > x + w:
                break
    if state:
        sx, sy, sw, sh = width - 328.0, 76.0, 294.0, 132.0
        review_id = f"ui-state:{screen_id}.{state.get('id', 'state')}"
        parts.extend(
            [
                f'<g class="diagram-object ui-state" data-review-id="{_esc(review_id)}" tabindex="0" role="button">',
                f'<rect x="{sx:.1f}" y="{sy:.1f}" width="{sw:.1f}" height="{sh:.1f}" rx="10" fill="#FFFAEB" stroke="#F79009" stroke-width="1.7"/>',
                f'<text class="ui-state-title" x="{sx + 12:.1f}" y="{sy + 23:.1f}">Rendered state · {_esc(state.get("name", state.get("id", "")))}</text>',
                f'<text class="ui-state-copy" x="{sx + 12:.1f}" y="{sy + 43:.1f}">Trigger: {_esc(state.get("trigger", ""))}</text>',
                f'<text class="ui-state-copy" x="{sx + 12:.1f}" y="{sy + 62:.1f}">{_esc(str(state.get("content", ""))[:78])}</text>',
                f'<text class="ui-state-copy" x="{sx + 12:.1f}" y="{sy + 84:.1f}">Focus: {_esc(state.get("focus_target", ""))}</text>',
                f'<text class="ui-state-copy" x="{sx + 12:.1f}" y="{sy + 104:.1f}">Announces: {_esc(state.get("announcement", ""))}</text>',
                f'<circle class="review-dot" data-dot-for="{_esc(review_id)}" cx="{sx + sw - 12:.1f}" cy="{sy + 14:.1f}" r="5"/>',
                '</g>',
            ]
        )
    legend = _legend_svg(view, {}, {})
    return (
        f'<svg class="architecture-svg ui-wireframe-svg" data-view-id="{_esc(view["id"])}" viewBox="0 0 {width:.0f} {height:.0f}" role="img" aria-label="{_esc(view.get("title", view["id"]))}">'
        f'<rect class="canvas-bg" width="{width:.0f}" height="{height:.0f}" rx="16"/>{"".join(parts)}{legend}</svg>'
    )


def _user_flow_svg(view: dict[str, Any], ui_spec: dict[str, Any]) -> str:
    screens, _components, flows, personas = _ui_indexes(ui_spec)
    flow = flows.get(view.get("flow"), {})
    persona = personas.get(flow.get("actor"), {})
    steps = [item for item in flow.get("steps", []) if isinstance(item, dict)]
    width, height = float(view.get("width", 1600)), float(view.get("height", 900))
    marker = f"ui-flow-arrow-{_esc(view['id'])}"
    parts = [
        f'<defs><marker id="{marker}" markerWidth="10" markerHeight="8" refX="9" refY="4" orient="auto"><path d="M0,0 L10,4 L0,8 z" fill="#2563EB"/></marker></defs>',
        f'<g class="diagram-object ui-persona" data-review-id="ui-persona:{_esc(persona.get("id", flow.get("actor", "persona")))}" tabindex="0" role="button">',
        '<circle cx="112" cy="126" r="29" fill="#E8F0FE" stroke="#4F6BED" stroke-width="2"/>',
        '<path d="M62 218 C66 165 158 165 162 218" fill="#E8F0FE" stroke="#4F6BED" stroke-width="2"/>',
        f'<text class="ui-persona-title" x="112" y="250" text-anchor="middle">{_esc(persona.get("name", flow.get("actor", "Persona")))}</text>',
        f'<text class="ui-region-meta" x="112" y="270" text-anchor="middle">{_esc(str(flow.get("goal", ""))[:34])}</text>',
        '</g>',
    ]
    card_x, card_w, card_h, gap = 245.0, min(460.0, max(320.0, width - 680.0)), 98.0, 28.0
    previous = (162.0, 192.0)
    for index, step in enumerate(steps, start=1):
        y = 84.0 + (index - 1) * (card_h + gap)
        screen = screens.get(step.get("screen"), {})
        review_id = f"ui-flow-step:{flow.get('id', 'flow')}.{step.get('id', index)}"
        sx, sy = previous
        tx, ty = card_x, y + card_h / 2
        parts.append(f'<path class="flow-line" d="M {sx:.1f} {sy:.1f} H {(sx + tx) / 2:.1f} V {ty:.1f} H {tx:.1f}" marker-end="url(#{marker})"/>')
        parts.extend(
            [
                f'<g class="diagram-object ui-flow-step" data-review-id="{_esc(review_id)}" tabindex="0" role="button">',
                f'<rect x="{card_x:.1f}" y="{y:.1f}" width="{card_w:.1f}" height="{card_h:.1f}" rx="10" fill="#FFFFFF" stroke="#2E90FA" stroke-width="1.8"/>',
                f'<text class="ui-region-title" x="{card_x + 12:.1f}" y="{y + 23:.1f}">{index}. {_esc(step.get("action", ""))}</text>',
                f'<text class="ui-region-meta" x="{card_x + 12:.1f}" y="{y + 43:.1f}">{_esc(screen.get("name", step.get("screen", "")))} · {_esc(screen.get("route", ""))}</text>',
                f'<text class="ui-region-copy" x="{card_x + 12:.1f}" y="{y + 64:.1f}">Outcome: {_esc(str(step.get("outcome", ""))[:72])}</text>',
                f'<text class="ui-exception" x="{card_x + 12:.1f}" y="{y + 84:.1f}">{_esc("Exception: " + str(step.get("alternate"))) if step.get("alternate") else ""}</text>',
                f'<circle class="review-dot" data-dot-for="{_esc(review_id)}" cx="{card_x + card_w - 12:.1f}" cy="{y + 13:.1f}" r="5"/>',
                '</g>',
            ]
        )
        previous = (card_x + card_w, y + card_h / 2)
    summary_x = card_x + card_w + 55.0
    summary_w = max(260.0, width - summary_x - 34.0)
    flow_review = f"ui-flow:{flow.get('id', 'flow')}"
    parts.extend(
        [
            f'<g class="diagram-object ui-flow-summary" data-review-id="{_esc(flow_review)}" tabindex="0" role="button">',
            f'<rect x="{summary_x:.1f}" y="84" width="{summary_w:.1f}" height="248" rx="10" fill="#F0FDF4" stroke="#12B76A" stroke-width="1.7"/>',
            f'<text class="ui-state-title" x="{summary_x + 12:.1f}" y="108">Success outcomes</text>',
            f'<text class="ui-state-copy" x="{summary_x + 12:.1f}" y="130">{_esc(" · ".join(flow.get("outcomes", []))[:120])}</text>',
            f'<text class="ui-state-title" x="{summary_x + 12:.1f}" y="172">Exception paths</text>',
            f'<text class="ui-state-copy" x="{summary_x + 12:.1f}" y="194">{_esc(" · ".join(flow.get("exceptions", []))[:150])}</text>',
            f'<circle class="review-dot" data-dot-for="{_esc(flow_review)}" cx="{summary_x + summary_w - 12:.1f}" cy="98" r="5"/>',
            '</g>',
        ]
    )
    legend = _legend_svg(view, {}, {})
    return (
        f'<svg class="architecture-svg ui-flow-svg" data-view-id="{_esc(view["id"])}" viewBox="0 0 {width:.0f} {height:.0f}" role="img" aria-label="{_esc(view.get("title", view["id"]))}">'
        f'<rect class="canvas-bg" width="{width:.0f}" height="{height:.0f}" rx="16"/>{"".join(parts)}{legend}</svg>'
    )


def _ui_state_map_svg(view: dict[str, Any], ui_spec: dict[str, Any]) -> str:
    screens, _components, _flows, _personas = _ui_indexes(ui_spec)
    screen = screens.get(view.get("screen"), {})
    states = [item for item in screen.get("states", []) if isinstance(item, dict)]
    width, height = float(view.get("width", 1600)), float(view.get("height", 900))
    columns, gap, margin, top, card_h = 2, 24.0, 34.0, 78.0, 142.0
    card_w = (width - margin * 2 - gap) / columns
    cards = []
    screen_id = str(screen.get("id", "screen"))
    for index, state in enumerate(states):
        x = margin + (index % columns) * (card_w + gap)
        y = top + (index // columns) * (card_h + gap)
        review_id = f"ui-state:{screen_id}.{state.get('id', index)}"
        actions = ", ".join(state.get("available_actions", [])) or "None"
        cards.append(
            f'<g class="diagram-object ui-state-card" data-review-id="{_esc(review_id)}" tabindex="0" role="button">'
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{card_w:.1f}" height="{card_h:.1f}" rx="10" fill="#FFFFFF" stroke="#7A5AF8" stroke-width="1.8"/>'
            f'<text class="ui-state-title" x="{x + 12:.1f}" y="{y + 24:.1f}">{_esc(state.get("name", state.get("id", "State")))} · {_esc(state.get("kind", ""))}</text>'
            f'<text class="ui-state-copy" x="{x + 12:.1f}" y="{y + 46:.1f}">Trigger: {_esc(str(state.get("trigger", ""))[:86])}</text>'
            f'<text class="ui-state-copy" x="{x + 12:.1f}" y="{y + 67:.1f}">{_esc(str(state.get("content", ""))[:94])}</text>'
            f'<text class="ui-state-copy" x="{x + 12:.1f}" y="{y + 91:.1f}">Actions: {_esc(actions)}</text>'
            f'<text class="ui-state-copy" x="{x + 12:.1f}" y="{y + 111:.1f}">Focus: {_esc(state.get("focus_target", ""))}</text>'
            f'<text class="ui-state-copy" x="{x + 12:.1f}" y="{y + 131:.1f}">Announcement: {_esc(state.get("announcement", ""))}</text>'
            f'<circle class="review-dot" data-dot-for="{_esc(review_id)}" cx="{x + card_w - 12:.1f}" cy="{y + 14:.1f}" r="5"/>'
            '</g>'
        )
    legend = _legend_svg(view, {}, {})
    return (
        f'<svg class="architecture-svg ui-state-map-svg" data-view-id="{_esc(view["id"])}" viewBox="0 0 {width:.0f} {height:.0f}" role="img" aria-label="{_esc(view.get("title", view["id"]))}">'
        f'<rect class="canvas-bg" width="{width:.0f}" height="{height:.0f}" rx="16"/>{"".join(cards)}{legend}</svg>'
    )


def render_review_html(model: dict[str, Any], findings: list[dict[str, Any]], digest: str, generator_version: str = "1.0.0") -> bytes:
    components = {item["id"]: item for item in model.get("components", []) if isinstance(item, dict) and item.get("id")}
    relationships = {item["id"]: item for item in model.get("relationships", []) if isinstance(item, dict) and item.get("id")}
    ui_spec = model.get("ui_spec", {}) if isinstance(model.get("ui_spec"), dict) else {}
    pages = []
    for index, view in enumerate(model.get("views", [])):
        if not isinstance(view, dict) or not view.get("id"):
            continue
        if view.get("type") == "sequence":
            svg = _sequence_svg(view, components, relationships)
        elif view.get("type") == "ui-wireframe":
            svg = _ui_wireframe_svg(view, ui_spec)
        elif view.get("type") == "user-flow":
            svg = _user_flow_svg(view, ui_spec)
        elif view.get("type") == "ui-state-map":
            svg = _ui_state_map_svg(view, ui_spec)
        else:
            svg = _graph_svg(view, components, relationships)
        hidden = "" if index == 0 else " hidden"
        pages.append(
            f'<section class="diagram-page{hidden}" data-page="{_esc(view["id"])}"><div class="view-heading"><div><p class="eyebrow">{_esc(view.get("type", "view"))}</p><h2>{_esc(view.get("title", view["id"]))}</h2><p>{_esc(view.get("purpose", ""))}</p></div><button class="review-view secondary" data-review-id="view:{_esc(view["id"])}">Review this view</button></div><div class="svg-frame">{svg}</div></section>'
        )
    project = model.get("project", {})
    title = str(project.get("title", "Architecture review"))
    summary = {
        "status": "pass" if not any(item.get("level") == "blocker" and not item.get("waived_by") for item in findings) else "fail",
        "blocking": sum(1 for item in findings if item.get("level") == "blocker" and not item.get("waived_by")),
        "warnings": sum(1 for item in findings if item.get("level") == "warning"),
        "waived": sum(1 for item in findings if item.get("waived_by")),
    }
    rendered = REVIEW_TEMPLATE
    replacements = {
        "__PAGE_TITLE__": _esc(title),
        "__PROJECT_TITLE__": _esc(title),
        "__PROJECT_ID__": _esc(project.get("id", "project")),
        "__PROJECT_VERSION__": _esc(project.get("version", "0")),
        "__PROJECT_STATUS__": _esc(project.get("status", "draft")),
        "__MODEL_DIGEST__": _esc(digest),
        "__GATE_STATUS__": _esc(summary["status"]),
        "__BLOCKING_COUNT__": str(summary["blocking"]),
        "__WARNING_COUNT__": str(summary["warnings"]),
        "__VIEW_PAGES__": "".join(pages),
        "__MODEL_JSON__": _json_for_script(model),
        "__FINDINGS_JSON__": _json_for_script(findings),
        "__SUMMARY_JSON__": _json_for_script(summary),
        "__GENERATOR_VERSION__": _esc(generator_version),
    }
    for key, value in replacements.items():
        rendered = rendered.replace(key, value)
    return rendered.encode("utf-8")


REVIEW_TEMPLATE = r'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta http-equiv="Content-Security-Policy" content="default-src 'self' data:; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; form-action 'self'">
  <title>__PAGE_TITLE__ · Architecture review</title>
  <style>
    :root{color-scheme:light;--bg:#f5f7fb;--surface:#fff;--surface-2:#f8fafc;--ink:#101828;--muted:#667085;--line:#d0d5dd;--blue:#175cd3;--blue-soft:#eff8ff;--green:#067647;--green-soft:#ecfdf3;--amber:#b54708;--amber-soft:#fffaeb;--red:#b42318;--red-soft:#fef3f2;--purple:#6941c6;--shadow:0 12px 36px rgba(16,24,40,.10)}
    *{box-sizing:border-box} html,body{height:100%;margin:0} body{font-family:Inter,ui-sans-serif,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:var(--bg);color:var(--ink);overflow:hidden}
    button,input,textarea,select{font:inherit} button{cursor:pointer} button:focus-visible,[tabindex]:focus-visible,input:focus-visible,textarea:focus-visible{outline:3px solid #84caff;outline-offset:2px}
    .app{display:grid;grid-template-rows:72px minmax(0,1fr);height:100%}
    header{display:flex;align-items:center;gap:18px;padding:11px 18px;background:var(--surface);border-bottom:1px solid var(--line);z-index:5}
    .brand{display:flex;align-items:center;gap:10px;min-width:220px}.logo{display:grid;place-items:center;width:40px;height:40px;border-radius:11px;background:#0b4a6f;color:#fff;font-weight:800;letter-spacing:-.04em}.brand strong{display:block}.brand small{color:var(--muted)}
    .project{min-width:0;flex:1}.project h1{font-size:16px;margin:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.meta{display:flex;align-items:center;gap:7px;margin-top:5px;color:var(--muted);font-size:12px}.pill{display:inline-flex;align-items:center;border:1px solid var(--line);border-radius:999px;padding:2px 8px;background:#fff}.pill.pass{color:var(--green);border-color:#abefc6;background:var(--green-soft)}.pill.fail{color:var(--red);border-color:#fecdca;background:var(--red-soft)}
    .header-actions{display:flex;align-items:center;gap:8px}.header-actions input{width:145px;padding:9px 10px;border:1px solid var(--line);border-radius:8px}.primary,.secondary,.ghost,.status-btn{border-radius:8px;padding:9px 12px;border:1px solid transparent;font-weight:650}.primary{background:#0b4a6f;color:#fff}.secondary{background:#fff;border-color:var(--line);color:#344054}.ghost{background:transparent;color:#475467}.primary:hover{background:#073a58}.secondary:hover,.ghost:hover{background:var(--surface-2)}
    .workspace{display:grid;grid-template-columns:254px minmax(0,1fr) 354px;min-height:0}
    aside{background:var(--surface);min-height:0;overflow:auto}.left{border-right:1px solid var(--line);padding:16px 12px}.right{border-left:1px solid var(--line);padding:18px}.section-title{font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);font-weight:750;margin:4px 8px 9px}.view-list,.object-list{display:grid;gap:4px}.view-button,.object-button{display:flex;width:100%;align-items:center;gap:9px;text-align:left;padding:10px;border:0;border-radius:9px;background:transparent;color:#344054}.view-button:hover,.view-button.active,.object-button:hover{background:var(--blue-soft);color:#1849a9}.view-index{display:grid;place-items:center;min-width:24px;height:24px;border-radius:7px;background:#eef2f6;color:#475467;font-size:11px;font-weight:750}.view-button.active .view-index{background:#d1e9ff;color:#175cd3}.view-copy{min-width:0}.view-copy strong{display:block;font-size:12px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.view-copy small{display:block;color:var(--muted);font-size:10px;margin-top:2px}.nav-divider{height:1px;background:var(--line);margin:15px 6px}.queue{display:grid;grid-template-columns:repeat(2,1fr);gap:7px;margin:0 6px}.queue-card{border:1px solid var(--line);border-radius:9px;padding:9px;background:var(--surface-2)}.queue-card strong{display:block;font-size:17px}.queue-card small{font-size:10px;color:var(--muted)}
    main{min-width:0;min-height:0;overflow:auto;padding:18px 20px 36px}.diagram-page{max-width:1900px;margin:0 auto}.diagram-page[hidden]{display:none}.view-heading{display:flex;justify-content:space-between;gap:20px;align-items:end;margin:0 0 12px}.view-heading h2{font-size:20px;margin:1px 0 5px}.view-heading p{margin:0;color:var(--muted);font-size:12px}.eyebrow{text-transform:uppercase;letter-spacing:.08em;font-weight:750;color:var(--blue)!important;font-size:10px!important}.svg-frame{background:#fff;border:1px solid var(--line);border-radius:16px;box-shadow:var(--shadow);overflow:auto;min-height:520px}.architecture-svg{display:block;width:100%;height:auto;min-width:900px;background:#fff}.canvas-bg{fill:#fff}.boundary-label{font-size:12px;font-weight:700;fill:#344054}.node-label{font-size:13px;font-weight:700}.node-tech{font-size:9px;font-weight:500;fill:#667085}.node-badge{font-size:8px;font-weight:800;fill:#fff}.lifecycle{font-size:8px;font-weight:800;fill:#667085}.edge-line,.sequence-message{fill:none;stroke-width:2}.edge-hit{fill:none;stroke:transparent;stroke-width:18}.edge-label-bg{fill:#fff;stroke:#eaecf0;stroke-width:1}.edge-label{font-size:10px;font-weight:700;fill:#344054}.edge-tech{font-size:8px;fill:#667085}.diagram-object{cursor:pointer}.diagram-object:hover rect:not(.edge-label-bg),.diagram-object:focus rect:not(.edge-label-bg){stroke-width:3}.diagram-object.selected rect:not(.edge-label-bg){stroke:#175cd3;stroke-width:4}.diagram-object.selected .edge-line,.diagram-object.selected .sequence-message{stroke-width:4}.review-dot{fill:#98a2b3;stroke:#fff;stroke-width:2}.review-dot.accepted{fill:#12b76a}.review-dot.rejected{fill:#f04438}.review-dot.modify{fill:#f79009}.legend>rect{fill:#fff;stroke:#98a2b3}.legend-title{font-size:11px;font-weight:750;fill:#344054}.legend-item{font-size:9px;fill:#475467}.sequence-participant{font-size:11px;font-weight:750;fill:#344054}.sequence-tech{font-size:8px;fill:#667085}.lifeline{stroke:#98a2b3;stroke-width:1.5;stroke-dasharray:5 5}.ui-chrome{font-size:10px;fill:#475467}.ui-region-title,.ui-state-title,.ui-persona-title{font-size:11px;font-weight:750;fill:#101828}.ui-region-meta,.ui-state-copy{font-size:9px;fill:#667085}.ui-region-copy{font-size:9px;fill:#475467}.ui-action-label{font-size:8px;font-weight:700;fill:#344054}.ui-exception{font-size:8px;fill:#b54708}.flow-line{fill:none;stroke:#2563eb;stroke-width:2}
    .empty-detail{display:grid;place-items:center;text-align:center;min-height:55vh;color:var(--muted)}.empty-detail .icon{display:grid;place-items:center;width:48px;height:48px;border-radius:14px;background:var(--blue-soft);color:var(--blue);font-size:22px;margin:auto}.detail-content[hidden],.empty-detail[hidden]{display:none}.detail-kicker{font-size:10px;text-transform:uppercase;letter-spacing:.09em;color:var(--blue);font-weight:800}.detail-content h2{font-size:19px;margin:5px 0}.detail-summary{color:var(--muted);font-size:12px;line-height:1.5}.detail-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:15px 0}.detail-field{padding:9px;border:1px solid var(--line);border-radius:9px;background:var(--surface-2)}.detail-field small{display:block;color:var(--muted);font-size:9px;text-transform:uppercase;letter-spacing:.06em}.detail-field strong{display:block;font-size:11px;margin-top:4px;overflow-wrap:anywhere}.status-group{display:grid;grid-template-columns:repeat(4,1fr);gap:5px;margin:11px 0}.status-btn{padding:8px 3px;font-size:10px;background:#fff;border-color:var(--line);color:#475467}.status-btn.active[data-status=accepted]{background:var(--green-soft);border-color:#75e0a7;color:var(--green)}.status-btn.active[data-status=rejected]{background:var(--red-soft);border-color:#fda29b;color:var(--red)}.status-btn.active[data-status=modify]{background:var(--amber-soft);border-color:#fec84b;color:var(--amber)}.right label{display:block;font-size:11px;font-weight:700;margin:14px 0 6px}.right textarea{width:100%;min-height:100px;resize:vertical;padding:10px;border:1px solid var(--line);border-radius:9px;line-height:1.45}.json-details{margin-top:14px;border-top:1px solid var(--line);padding-top:12px}.json-details summary{font-size:11px;font-weight:700;cursor:pointer}.json-details pre{white-space:pre-wrap;word-break:break-word;font-size:9px;color:#475467;background:var(--surface-2);border-radius:8px;padding:9px;max-height:260px;overflow:auto}.save-state{font-size:10px;color:var(--muted);min-height:16px;margin-top:8px}
    .chat-button{position:fixed;right:374px;bottom:22px;width:52px;height:52px;border:0;border-radius:16px;background:#0b4a6f;color:#fff;font-size:23px;box-shadow:var(--shadow);z-index:10}.chat-panel{position:fixed;right:374px;bottom:84px;width:min(430px,calc(100vw - 40px));height:min(590px,calc(100vh - 120px));display:grid;grid-template-rows:auto 1fr auto;background:#fff;border:1px solid var(--line);border-radius:15px;box-shadow:0 24px 64px rgba(16,24,40,.22);z-index:11}.chat-panel[hidden]{display:none}.chat-head{display:flex;justify-content:space-between;align-items:center;padding:13px 14px;border-bottom:1px solid var(--line)}.chat-head strong{font-size:13px}.chat-head small{display:block;color:var(--muted);font-size:10px;margin-top:2px}.chat-messages{padding:14px;overflow:auto;background:var(--surface-2)}.message{max-width:88%;padding:9px 11px;border-radius:11px;margin-bottom:9px;font-size:11px;line-height:1.5;white-space:pre-wrap}.message.assistant{background:#fff;border:1px solid var(--line)}.message.user{background:#0b4a6f;color:#fff;margin-left:auto}.message.system{background:var(--amber-soft);border:1px solid #fedf89;color:#93370d;max-width:100%}.chat-compose{padding:11px;border-top:1px solid var(--line)}.chat-compose textarea{width:100%;height:72px;resize:none;border:1px solid var(--line);border-radius:9px;padding:9px}.chat-compose div{display:flex;justify-content:space-between;align-items:center;margin-top:7px}.chat-compose small{font-size:9px;color:var(--muted)}
    .toast{position:fixed;left:50%;bottom:22px;transform:translateX(-50%);background:#101828;color:#fff;padding:10px 14px;border-radius:9px;font-size:11px;box-shadow:var(--shadow);z-index:30}.toast[hidden]{display:none}
    @media(max-width:1180px){.workspace{grid-template-columns:220px minmax(0,1fr)}.right{position:fixed;right:0;top:72px;bottom:0;width:354px;box-shadow:var(--shadow);z-index:8}.right.closed{display:none}.chat-button,.chat-panel{right:22px}.header-actions .hide-small{display:none}}
    @media(max-width:760px){body{overflow:auto}.app{height:auto;min-height:100%}.workspace{display:block}.left{border:0;border-bottom:1px solid var(--line)}main{overflow:visible}.right{position:static;width:auto;border:0;box-shadow:none}.right.closed{display:block}.header-actions{display:none}.architecture-svg{min-width:760px}.chat-button,.chat-panel{right:16px}.chat-panel{bottom:80px}.brand{min-width:auto}.project .meta{display:none}}
  </style>
</head>
<body>
<div class="app">
  <header>
    <div class="brand"><div class="logo">AS</div><div><strong>Arch Studio</strong><small>Visual specification review</small></div></div>
    <div class="project"><h1>__PROJECT_TITLE__</h1><div class="meta"><span>__PROJECT_ID__</span><span>•</span><span>v__PROJECT_VERSION__</span><span class="pill">__PROJECT_STATUS__</span><span class="pill __GATE_STATUS__">Gate __GATE_STATUS__ · __BLOCKING_COUNT__ blockers · __WARNING_COUNT__ warnings</span></div></div>
    <div class="header-actions"><input id="reviewer" class="hide-small" aria-label="Reviewer name" placeholder="Reviewer name"><button id="copyPrompt" class="secondary">Copy change prompt</button><button id="exportReview" class="primary">Export review JSON</button></div>
  </header>
  <div class="workspace">
    <aside class="left">
      <div class="section-title">Diagram views</div><div id="viewList" class="view-list"></div>
      <div class="nav-divider"></div>
      <div class="section-title">Review progress</div>
      <div class="queue"><div class="queue-card"><strong id="reviewedCount">0</strong><small>Reviewed</small></div><div class="queue-card"><strong id="changeCount">0</strong><small>Need change</small></div><div class="queue-card"><strong id="pendingCount">0</strong><small>Pending</small></div><div class="queue-card"><strong id="acceptedCount">0</strong><small>Accepted</small></div></div>
      <div class="nav-divider"></div>
      <div class="section-title">Review registers</div><div id="registerList" class="object-list"></div>
      <div class="nav-divider"></div>
      <button id="overallReview" class="view-button"><span class="view-index">✓</span><span class="view-copy"><strong>Overall disposition</strong><small>Approve or request revision</small></span></button>
    </aside>
    <main>__VIEW_PAGES__</main>
    <aside class="right">
      <div id="emptyDetail" class="empty-detail"><div><div class="icon">⌁</div><h3>Select a diagram object</h3><p>Click any component, connection, view, decision, risk, question, or finding to inspect and review it.</p></div></div>
      <div id="detailContent" class="detail-content" hidden>
        <div id="detailKicker" class="detail-kicker"></div><h2 id="detailTitle"></h2><p id="detailSummary" class="detail-summary"></p><div id="detailGrid" class="detail-grid"></div>
        <label>Review decision</label><div class="status-group"><button class="status-btn" data-status="pending">Pending</button><button class="status-btn" data-status="accepted">Accept</button><button class="status-btn" data-status="modify">Modify</button><button class="status-btn" data-status="rejected">Reject</button></div>
        <label for="reviewComment">Comment or requested change</label><textarea id="reviewComment" placeholder="Explain the reason, expected outcome, constraint, or alternative."></textarea><div id="saveState" class="save-state"></div>
        <details class="json-details"><summary>Complete architecture metadata</summary><pre id="detailJson"></pre></details>
      </div>
    </aside>
  </div>
</div>
<button id="chatButton" class="chat-button" aria-label="Open Claude architecture chat">✦</button>
<section id="chatPanel" class="chat-panel" hidden aria-label="Claude architecture chat">
  <div class="chat-head"><div><strong>Architecture copilot</strong><small id="bridgeStatus">Checking local bridge…</small></div><button id="closeChat" class="ghost" aria-label="Close chat">×</button></div>
  <div id="chatMessages" class="chat-messages"><div class="message assistant">Ask for a change to the visual specification. When the local Claude bridge is enabled, a structurally valid revision is applied and the review bundle is regenerated. Offline, use “Copy change prompt”.</div></div>
  <div class="chat-compose"><textarea id="chatInput" placeholder="Example: Keep the API private and route partner traffic through APIM with mTLS."></textarea><div><small>Model changes are validated before write.</small><button id="sendChat" class="primary">Send</button></div></div>
</section>
<div id="toast" class="toast" hidden></div>
<script id="arch-model" type="application/json">__MODEL_JSON__</script>
<script id="arch-findings" type="application/json">__FINDINGS_JSON__</script>
<script id="arch-summary" type="application/json">__SUMMARY_JSON__</script>
<script>
(() => {
  'use strict';
  const model=JSON.parse(document.getElementById('arch-model').textContent);
  const findings=JSON.parse(document.getElementById('arch-findings').textContent);
  const summary=JSON.parse(document.getElementById('arch-summary').textContent);
  const digest='__MODEL_DIGEST__'; const csrf='__ARCH_STUDIO_CSRF__'; const generator='__GENERATOR_VERSION__';
  const storageKey=`arch-studio:${model.project.id}:${model.project.version}:${digest}`;
  const kinds=['requirements','controls','components','relationships','views','decisions','risks','assumptions','open_questions','waivers'];
  const index={}; kinds.forEach(kind=>(model[kind]||[]).forEach(item=>{index[`${kind.replace('_','-').replace(/s$/,'')}:${item.id}`]={kind,item};}));
  const ui=model.ui_spec||{};
  [['personas','ui-persona'],['breakpoints','ui-breakpoint'],['flows','ui-flow'],['screens','ui-screen'],['components','ui-component'],['bindings','ui-binding'],['navigation','ui-navigation'],['analytics','ui-analytics']].forEach(([collection,kind])=>(ui[collection]||[]).forEach(item=>{index[`${kind}:${item.id}`]={kind,item};}));
  (ui.screens||[]).forEach(screen=>{(screen.regions||[]).forEach(region=>{index[`ui-region:${screen.id}.${region.id}`]={kind:'ui-region',item:region,screen};(region.actions||[]).forEach(action=>{index[`ui-action:${screen.id}.${action.id}`]={kind:'ui-action',item:action,screen,region};});});(screen.states||[]).forEach(item=>{index[`ui-state:${screen.id}.${item.id}`]={kind:'ui-state',item,screen};});});
  (ui.flows||[]).forEach(flow=>(flow.steps||[]).forEach(item=>{index[`ui-flow-step:${flow.id}.${item.id}`]={kind:'ui-flow-step',item,flow};}));
  (model.views||[]).forEach(view=>(view.interactions||[]).forEach(item=>{index[`interaction:${item.id}`]={kind:'interaction',item,view};}));
  findings.forEach((item,i)=>{index[`finding:${i}`]={kind:'finding',item:{...item,id:`finding-${i}`}};});
  index['overall:design']={kind:'overall',item:{id:'design',title:ui.status&&ui.status!=='not-requested'?'Overall architecture and UI disposition':'Overall architecture disposition',description:model.project.description}};
  let state={schema_version:'1.0',project_id:model.project.id,project_version:model.project.version,model_digest:digest,reviewer:'',overall:'pending',objects:{},updated_at:new Date().toISOString()};
  try{const saved=JSON.parse(localStorage.getItem(storageKey)||'null');if(saved&&saved.model_digest===digest)state={...state,...saved,objects:saved.objects||{}};}catch(_e){}
  let currentView=(model.views[0]||{}).id; let selected=null; let reviewSaveTimer=null;
  const $=id=>document.getElementById(id); const escapeHtml=value=>String(value??'').replace(/[&<>'"]/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[ch]));
  const titleFor=(kind,item)=>item.title||item.name||item.label||item.question||item.text||item.code||item.id;
  const summaryFor=(kind,item)=>item.description||item.purpose||item.message||item.context||item.mitigation||item.consequence||item.choice||'';
  function viewNav(){
    $('viewList').innerHTML=(model.views||[]).map((v,i)=>`<button class="view-button ${v.id===currentView?'active':''}" data-view="${escapeHtml(v.id)}"><span class="view-index">${String(i+1).padStart(2,'0')}</span><span class="view-copy"><strong>${escapeHtml(v.title)}</strong><small>${escapeHtml(v.type)}</small></span></button>`).join('');
    document.querySelectorAll('[data-view]').forEach(btn=>btn.addEventListener('click',()=>setView(btn.dataset.view)));
  }
  function registerNav(){
    const groups=[['ui-screen','UI screens',ui.screens||[]],['ui-flow','User flows',ui.flows||[]],['ui-component','UI components',ui.components||[]],['decision','Decisions',model.decisions||[]],['risk','Risks',model.risks||[]],['open-question','Open questions',model.open_questions||[]],['finding','Gate findings',findings]];
    $('registerList').innerHTML=groups.filter(g=>g[2].length).map(([kind,label,items])=>`<button class="object-button" data-register="${kind}"><span class="view-index">${items.length}</span><span class="view-copy"><strong>${label}</strong><small>${kind==='finding'?summary.blocking+' blocking':''}</small></span></button>`).join('');
    document.querySelectorAll('[data-register]').forEach(btn=>btn.addEventListener('click',()=>openRegister(btn.dataset.register)));
  }
  function setView(id){currentView=id;document.querySelectorAll('.diagram-page').forEach(page=>page.hidden=page.dataset.page!==id);viewNav();clearSelection();}
  function openRegister(kind){
    const keys=Object.keys(index).filter(key=>key.startsWith(kind+':'));
    if(!keys.length)return; selectObject(keys[0]);
    const right=document.querySelector('.right');right.classList.remove('closed');
  }
  function normalizedKey(key){return key==='overall:design'?key:key;}
  function reviewFor(key){return state.objects[key]||{status:'pending',comment:'',updated_at:null};}
  function selectObject(key){
    key=normalizedKey(key); const record=index[key]; if(!record)return; selected=key;
    document.querySelectorAll('.diagram-object.selected').forEach(el=>el.classList.remove('selected'));
    document.querySelectorAll(`[data-review-id="${CSS.escape(key)}"]`).forEach(el=>el.classList.add('selected'));
    $('emptyDetail').hidden=true;$('detailContent').hidden=false;
    const {kind,item}=record; $('detailKicker').textContent=kind.replaceAll('-',' ');$('detailTitle').textContent=titleFor(kind,item);$('detailSummary').textContent=summaryFor(kind,item);
    const fields=[];
    ['technology','owner','criticality','data_classification','status','mode','protocol','auth','route','role','kind','category','screen','region','operation','transport','authorization','trigger','focus_target','announcement','level','gate','subject','likelihood','impact','exposure','date','due','expires'].forEach(name=>{if(item[name]!==undefined&&item[name]!==''&&item[name]!==null)fields.push([name.replaceAll('_',' '),Array.isArray(item[name])?item[name].join(', '):item[name]]);});
    $('detailGrid').innerHTML=fields.slice(0,8).map(([k,v])=>`<div class="detail-field"><small>${escapeHtml(k)}</small><strong>${escapeHtml(v)}</strong></div>`).join('')||'<div class="detail-field"><small>Identifier</small><strong>'+escapeHtml(item.id)+'</strong></div>';
    $('detailJson').textContent=JSON.stringify(item,null,2); const review=reviewFor(key);$('reviewComment').value=review.comment||'';setStatusButtons(review.status||'pending');$('saveState').textContent=review.updated_at?`Saved locally ${new Date(review.updated_at).toLocaleString()}`:'Not reviewed yet';
  }
  function clearSelection(){selected=null;document.querySelectorAll('.diagram-object.selected').forEach(el=>el.classList.remove('selected'));$('emptyDetail').hidden=false;$('detailContent').hidden=true;}
  function setStatusButtons(status){document.querySelectorAll('.status-btn').forEach(btn=>btn.classList.toggle('active',btn.dataset.status===status));}
  function saveSelected(patch,rerender=true){if(!selected)return;const prior=reviewFor(selected);state.objects[selected]={...prior,...patch,updated_at:new Date().toISOString()};state.updated_at=new Date().toISOString();state.reviewer=$('reviewer').value.trim();if(selected==='overall:design')state.overall=state.objects[selected].status;persist();if(rerender)selectObject(selected);refreshDots();refreshCounts();}
  function persist(){
    localStorage.setItem(storageKey,JSON.stringify(state));
    if(location.protocol==='file:')return;
    clearTimeout(reviewSaveTimer);
    reviewSaveTimer=setTimeout(()=>fetch('/api/review',{method:'POST',headers:{'Content-Type':'application/json','X-Arch-Studio-Token':csrf},body:JSON.stringify(exportPayload())}).catch(()=>{}),350);
  }
  function refreshDots(){document.querySelectorAll('[data-dot-for]').forEach(dot=>{dot.classList.remove('accepted','rejected','modify');const status=reviewFor(dot.dataset.dotFor).status;if(status!=='pending')dot.classList.add(status);});}
  function reviewableKeys(){return Object.keys(index).filter(k=>!k.startsWith('requirement:')&&!k.startsWith('control:')&&!k.startsWith('assumption:')&&!k.startsWith('waiver:'));}
  function refreshCounts(){const keys=reviewableKeys();const values=keys.map(reviewFor);const reviewed=values.filter(v=>v.status&&v.status!=='pending').length;$('reviewedCount').textContent=reviewed;$('changeCount').textContent=values.filter(v=>v.status==='modify'||v.status==='rejected').length;$('acceptedCount').textContent=values.filter(v=>v.status==='accepted').length;$('pendingCount').textContent=Math.max(0,keys.length-reviewed);}
  function exportPayload(){return {...state,reviewer:$('reviewer').value.trim(),exported_at:new Date().toISOString(),generator_version:generator,gate_summary:summary};}
  function download(name,text,type){const blob=new Blob([text],{type});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
  function changePrompt(){const changes=Object.entries(state.objects).filter(([_k,v])=>v.status==='modify'||v.status==='rejected').map(([key,v])=>({object:key,status:v.status,comment:v.comment||''}));return `Use /arch-studio to revise ${model.project.id} version ${model.project.version}.\nModel SHA-256: ${digest}\nApply only the coherent changes below to the canonical .arch.json. Preserve unrelated architecture and UI stable IDs, contracts, and placements; update affected ADRs, risks, states, bindings, acceptance tests, assumptions, and traceability; then run a strict build and report the delta. Do not weaken a gate to make it pass.\n\nRequested changes:\n${JSON.stringify(changes,null,2)}`;}
  async function copyText(text){try{await navigator.clipboard.writeText(text);toast('Copied to clipboard');}catch(_e){download(`${model.project.id}-change-prompt.txt`,text,'text/plain');toast('Clipboard unavailable; downloaded prompt');}}
  function toast(message){$('toast').textContent=message;$('toast').hidden=false;setTimeout(()=>$('toast').hidden=true,2200);}
  async function bridgeHealth(){if(location.protocol==='file:'){$('bridgeStatus').textContent='Offline review · bridge not running';return false;}try{const response=await fetch('/api/health',{headers:{'X-Arch-Studio-Token':csrf}});const data=await response.json();$('bridgeStatus').textContent=data.claude_bridge?'Claude bridge enabled': 'Review server active · Claude bridge disabled';return !!data.claude_bridge;}catch(_e){$('bridgeStatus').textContent='Local bridge unavailable';return false;}}
  async function sendChat(){const message=$('chatInput').value.trim();if(!message)return;appendMessage('user',message);$('chatInput').value='';$('sendChat').disabled=true;try{const response=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json','X-Arch-Studio-Token':csrf},body:JSON.stringify({message,review:exportPayload()})});const data=await response.json();if(!response.ok)throw new Error(data.error||`Bridge error ${response.status}`);appendMessage('assistant',data.reply||'Revision processed.');if(data.applied){appendMessage('system','A structurally valid model revision was written and the bundle was regenerated. Reloading…');setTimeout(()=>location.reload(),900);}else if(data.validation&&data.validation.length){appendMessage('system','Candidate was not applied:\n'+data.validation.map(x=>`${x.code}: ${x.message}`).join('\n'));}}catch(error){appendMessage('system',error.message||String(error));}finally{$('sendChat').disabled=false;}}
  function appendMessage(role,text){const node=document.createElement('div');node.className=`message ${role}`;node.textContent=text;$('chatMessages').appendChild(node);$('chatMessages').scrollTop=$('chatMessages').scrollHeight;}
  document.addEventListener('click',event=>{const target=event.target.closest('[data-review-id]');if(target&&!target.classList.contains('status-btn')){event.preventDefault();selectObject(target.dataset.reviewId);}});
  document.addEventListener('keydown',event=>{if((event.key==='Enter'||event.key===' ')&&event.target.matches('.diagram-object')){event.preventDefault();selectObject(event.target.dataset.reviewId);}});
  document.querySelectorAll('.status-btn').forEach(btn=>btn.addEventListener('click',()=>saveSelected({status:btn.dataset.status,comment:$('reviewComment').value})));
  $('reviewComment').addEventListener('input',()=>{if(selected)saveSelected({comment:$('reviewComment').value},false);});
  $('reviewer').value=state.reviewer||'';$('reviewer').addEventListener('change',()=>{state.reviewer=$('reviewer').value.trim();persist();});
  $('exportReview').addEventListener('click',()=>download(`${model.project.id}-review-decisions.json`,JSON.stringify(exportPayload(),null,2),'application/json'));
  $('copyPrompt').addEventListener('click',()=>copyText(changePrompt()));
  $('overallReview').addEventListener('click',()=>selectObject('overall:design'));
  $('chatButton').addEventListener('click',()=>{$('chatPanel').hidden=!$('chatPanel').hidden;if(!$('chatPanel').hidden)bridgeHealth();});$('closeChat').addEventListener('click',()=>$('chatPanel').hidden=true);$('sendChat').addEventListener('click',sendChat);$('chatInput').addEventListener('keydown',event=>{if(event.key==='Enter'&&(event.ctrlKey||event.metaKey)){event.preventDefault();sendChat();}});
  viewNav();registerNav();refreshDots();refreshCounts();bridgeHealth();
})();
</script>
</body>
</html>
'''
