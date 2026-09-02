from __future__ import annotations

import hashlib
import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


KIND_STYLES: dict[str, dict[str, str]] = {
    "actor": {"fill": "#E8F0FE", "stroke": "#4F6BED", "font": "#172B4D"},
    "external-system": {"fill": "#F3F4F6", "stroke": "#667085", "font": "#1F2937"},
    "client": {"fill": "#EEF2FF", "stroke": "#6366F1", "font": "#1E1B4B"},
    "gateway": {"fill": "#E0F2FE", "stroke": "#0284C7", "font": "#0C4A6E"},
    "service": {"fill": "#ECFDF5", "stroke": "#059669", "font": "#064E3B"},
    "function": {"fill": "#FFF7ED", "stroke": "#EA580C", "font": "#7C2D12"},
    "worker": {"fill": "#F0FDFA", "stroke": "#0D9488", "font": "#134E4A"},
    "message-broker": {"fill": "#FFF7ED", "stroke": "#F97316", "font": "#7C2D12"},
    "database": {"fill": "#F5F3FF", "stroke": "#7C3AED", "font": "#4C1D95"},
    "cache": {"fill": "#FFF1F2", "stroke": "#E11D48", "font": "#881337"},
    "storage": {"fill": "#F5F3FF", "stroke": "#8B5CF6", "font": "#4C1D95"},
    "identity": {"fill": "#FEF3C7", "stroke": "#D97706", "font": "#78350F"},
    "security": {"fill": "#FEF2F2", "stroke": "#DC2626", "font": "#7F1D1D"},
    "observability": {"fill": "#F0FDFA", "stroke": "#0F766E", "font": "#134E4A"},
    "pipeline": {"fill": "#F8FAFC", "stroke": "#475569", "font": "#1E293B"},
    "repository": {"fill": "#F8FAFC", "stroke": "#64748B", "font": "#1E293B"},
    "kubernetes": {"fill": "#EFF6FF", "stroke": "#326CE5", "font": "#1E3A8A"},
    "network": {"fill": "#E0F2FE", "stroke": "#0369A1", "font": "#0C4A6E"},
    "generic": {"fill": "#FFFFFF", "stroke": "#667085", "font": "#101828"},
}
BOUNDARY_STYLES: dict[str, tuple[str, str]] = {
    "cloud": ("#EAF4FF", "#0078D4"),
    "tenant": ("#F2F7FC", "#0078D4"),
    "management-group": ("#F8FAFC", "#475569"),
    "subscription": ("#F4F8FC", "#2563EB"),
    "region": ("#F8FAFC", "#64748B"),
    "resource-group": ("#F8FAFC", "#94A3B8"),
    "vnet": ("#EFF6FF", "#3B82F6"),
    "subnet": ("#F0F9FF", "#38BDF8"),
    "cluster": ("#EEF2FF", "#326CE5"),
    "namespace": ("#F5F3FF", "#8B5CF6"),
    "trust": ("#FFF7ED", "#F97316"),
    "data-residency": ("#FDF4FF", "#C026D3"),
    "failure-domain": ("#FEF2F2", "#EF4444"),
    "system": ("#F8FAFC", "#64748B"),
    "generic": ("#F8FAFC", "#94A3B8"),
}
EDGE_STYLES: dict[str, dict[str, str]] = {
    "sync": {"stroke": "#2563EB", "dash": "0", "arrow": "block"},
    "async": {"stroke": "#EA580C", "dash": "1", "arrow": "block"},
    "batch": {"stroke": "#7C3AED", "dash": "1", "arrow": "block"},
    "stream": {"stroke": "#0F766E", "dash": "0", "arrow": "block"},
    "return": {"stroke": "#64748B", "dash": "1", "arrow": "open"},
}


def load_icons(path: str | Path) -> dict[str, dict[str, str]]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Azure icon catalog must be an object")
    return data


def _safe_id(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", value)


def _diagram_id(view_id: str) -> str:
    return hashlib.sha1(view_id.encode("utf-8")).hexdigest()[:12]


def _cell(
    root: ET.Element,
    *,
    cell_id: str,
    value: str = "",
    style: str = "",
    parent: str = "1",
    vertex: bool = False,
    edge: bool = False,
    source: str | None = None,
    target: str | None = None,
    arch_id: str | None = None,
    arch_kind: str | None = None,
) -> ET.Element:
    attributes = {"id": cell_id, "value": value, "style": style, "parent": parent}
    if vertex:
        attributes["vertex"] = "1"
    if edge:
        attributes["edge"] = "1"
    if source:
        attributes["source"] = source
    if target:
        attributes["target"] = target
    if arch_id:
        attributes["arch-id"] = arch_id
    if arch_kind:
        attributes["arch-kind"] = arch_kind
    return ET.SubElement(root, "mxCell", attributes)


def _geometry(
    cell: ET.Element,
    *,
    x: float | None = None,
    y: float | None = None,
    w: float | None = None,
    h: float | None = None,
    relative: bool = False,
) -> ET.Element:
    attributes: dict[str, str] = {"as": "geometry"}
    if x is not None:
        attributes["x"] = _number(x)
    if y is not None:
        attributes["y"] = _number(y)
    if w is not None:
        attributes["width"] = _number(w)
    if h is not None:
        attributes["height"] = _number(h)
    if relative:
        attributes["relative"] = "1"
    return ET.SubElement(cell, "mxGeometry", attributes)


def _number(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else f"{value:.2f}".rstrip("0").rstrip(".")


def _node_style(component: dict[str, Any], icons: dict[str, dict[str, str]]) -> str:
    kind = component.get("kind", "generic")
    colors = KIND_STYLES.get(kind, KIND_STYLES["generic"])
    azure_id = component.get("azure_service")
    icon = icons.get(azure_id, {}) if azure_id else {}
    base = (
        "html=1;whiteSpace=wrap;rounded=1;arcSize=12;shadow=0;glass=0;"
        f"fillColor={colors['fill']};strokeColor={colors['stroke']};fontColor={colors['font']};"
        "strokeWidth=1.5;fontFamily=Helvetica;fontSize=12;align=center;verticalAlign=middle;"
        "spacing=8;"
    )
    if icon.get("image"):
        base += (
            "shape=label;imageAspect=0;imageAlign=center;imageVerticalAlign=top;"
            f"image={icon['image']};imageWidth=40;imageHeight=40;spacingTop=42;"
        )
    elif kind == "database":
        base += "shape=cylinder3;boundedLbl=1;size=12;"
    elif kind == "actor":
        base += "shape=mxgraph.basic.person;"
    return base


def _node_label(component: dict[str, Any]) -> str:
    name = str(component.get("name", component.get("id", "Component")))
    technology = str(component.get("technology", ""))
    lifecycle = str(component.get("lifecycle", ""))
    suffix = ""
    if technology:
        suffix += f'<br><span style="font-size:10px;color:#475467">{technology}</span>'
    if lifecycle in {"new", "changed", "retiring"}:
        suffix += f'<br><span style="font-size:9px;color:#667085;text-transform:uppercase">{lifecycle}</span>'
    return f"<b>{name}</b>{suffix}"


def _edge_style(relationship: dict[str, Any]) -> str:
    mode = relationship.get("mode", "sync")
    item = EDGE_STYLES.get(mode, EDGE_STYLES["sync"])
    return (
        "edgeStyle=orthogonalEdgeStyle;orthogonalLoop=1;jettySize=auto;html=1;rounded=0;"
        f"strokeColor={item['stroke']};strokeWidth=2;dashed={item['dash']};endArrow={item['arrow']};"
        "endFill=1;fontFamily=Helvetica;fontSize=10;fontColor=#344054;"
        "labelBackgroundColor=#FFFFFF;labelBorderColor=none;spacing=4;"
    )


def _edge_label(relationship: dict[str, Any]) -> str:
    label = str(relationship.get("label", ""))
    technical: list[str] = []
    protocol = relationship.get("protocol")
    port = relationship.get("port")
    if protocol:
        technical.append(f"{protocol}/{port}" if port not in (None, "") else str(protocol))
    if relationship.get("auth"):
        technical.append(str(relationship["auth"]))
    if relationship.get("mode"):
        technical.append(str(relationship["mode"]))
    return f"<b>{label}</b>" + (f'<br><span style="font-size:9px;color:#667085">{" · ".join(technical)}</span>' if technical else "")


def _boundary_style(kind: str) -> str:
    fill, stroke = BOUNDARY_STYLES.get(kind, BOUNDARY_STYLES["generic"])
    dashed = "1" if kind in {"trust", "data-residency", "failure-domain"} else "0"
    return (
        "swimlane;html=1;rounded=1;arcSize=10;horizontal=1;startSize=30;collapsible=0;"
        "container=1;recursiveResize=0;whiteSpace=wrap;shadow=0;"
        f"fillColor={fill};swimlaneFillColor=#FFFFFF;strokeColor={stroke};dashed={dashed};"
        "strokeWidth=1.5;fontStyle=1;fontSize=12;fontColor=#344054;align=left;spacingLeft=10;"
    )


def render_drawio(model: dict[str, Any], icons: dict[str, dict[str, str]], generator_version: str = "1.0.0") -> bytes:
    reviewed_at = str(model.get("project", {}).get("reviewed_at", ""))
    try:
        modified = datetime.fromisoformat(reviewed_at[:10]).replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")
    except ValueError:
        modified = "1970-01-01T00:00:00Z"
    mxfile = ET.Element(
        "mxfile",
        {
            "host": "Arch Studio",
            "modified": modified,
            "agent": f"arch-studio/{generator_version}",
            "version": "24.7.17",
            "type": "device",
            "compressed": "false",
            "pages": str(len(model.get("views", []))),
        },
    )
    components = {item["id"]: item for item in model.get("components", []) if isinstance(item, dict) and item.get("id")}
    relationships = {item["id"]: item for item in model.get("relationships", []) if isinstance(item, dict) and item.get("id")}
    ui_spec = model.get("ui_spec", {}) if isinstance(model.get("ui_spec"), dict) else {}
    for view in model.get("views", []):
        if not isinstance(view, dict) or not view.get("id"):
            continue
        diagram = ET.SubElement(mxfile, "diagram", {"id": _diagram_id(view["id"]), "name": str(view.get("title", view["id"]))})
        graph = ET.SubElement(
            diagram,
            "mxGraphModel",
            {
                "dx": "1422",
                "dy": "794",
                "grid": "1",
                "gridSize": "10",
                "guides": "1",
                "tooltips": "1",
                "connect": "1",
                "arrows": "1",
                "fold": "1",
                "page": "1",
                "pageScale": "1",
                "pageWidth": _number(float(view.get("width", 1600))),
                "pageHeight": _number(float(view.get("height", 900))),
                "math": "0",
                "shadow": "0",
            },
        )
        root = ET.SubElement(graph, "root")
        ET.SubElement(root, "mxCell", {"id": "0"})
        ET.SubElement(root, "mxCell", {"id": "1", "parent": "0"})
        _render_title(root, view)
        if view.get("type") == "sequence":
            _render_sequence(root, view, components)
        elif view.get("type") == "ui-wireframe":
            _render_ui_wireframe(root, view, ui_spec)
        elif view.get("type") == "user-flow":
            _render_user_flow(root, view, ui_spec)
        elif view.get("type") == "ui-state-map":
            _render_ui_state_map(root, view, ui_spec)
        else:
            _render_graph(root, view, components, relationships, icons)
        _render_legend(root, view, components, relationships)
    xml = ET.tostring(mxfile, encoding="utf-8", xml_declaration=True)
    ET.fromstring(xml)
    return xml


def _render_title(root: ET.Element, view: dict[str, Any]) -> None:
    title = _cell(
        root,
        cell_id=f"{_safe_id(view['id'])}-title",
        value=f"<b>{view.get('title', view['id'])}</b>",
        style="text;html=1;align=left;verticalAlign=middle;whiteSpace=wrap;rounded=0;fontFamily=Helvetica;fontSize=20;fontColor=#101828;fontStyle=1;",
        vertex=True,
        arch_id=view["id"],
        arch_kind="view-title",
    )
    _geometry(title, x=24, y=16, w=max(400, float(view.get("width", 1600)) - 48), h=34)
    purpose = _cell(
        root,
        cell_id=f"{_safe_id(view['id'])}-purpose",
        value=str(view.get("purpose", "")),
        style="text;html=1;align=left;verticalAlign=middle;whiteSpace=wrap;rounded=0;fontFamily=Helvetica;fontSize=11;fontColor=#475467;",
        vertex=True,
    )
    _geometry(purpose, x=24, y=50, w=max(400, float(view.get("width", 1600)) - 48), h=28)


def _render_graph(
    root: ET.Element,
    view: dict[str, Any],
    components: dict[str, dict[str, Any]],
    relationships: dict[str, dict[str, Any]],
    icons: dict[str, dict[str, str]],
) -> None:
    prefix = _safe_id(view["id"])
    boundaries = {item["id"]: item for item in view.get("boundaries", []) if isinstance(item, dict) and item.get("id")}
    boundary_cells: dict[str, str] = {}
    unresolved = set(boundaries)
    while unresolved:
        progressed = False
        for boundary_id in list(unresolved):
            boundary = boundaries[boundary_id]
            parent_id = boundary.get("parent")
            if parent_id and parent_id not in boundary_cells:
                continue
            parent_cell = boundary_cells.get(parent_id, "1")
            parent_boundary = boundaries.get(parent_id) if parent_id else None
            x = float(boundary.get("x", 0)) - (float(parent_boundary.get("x", 0)) if parent_boundary else 0)
            y = float(boundary.get("y", 0)) - (float(parent_boundary.get("y", 0)) if parent_boundary else 0)
            cell_id = f"{prefix}-boundary-{_safe_id(boundary_id)}"
            cell = _cell(
                root,
                cell_id=cell_id,
                value=str(boundary.get("label", boundary_id)),
                style=_boundary_style(str(boundary.get("kind", "generic"))),
                parent=parent_cell,
                vertex=True,
                arch_id=boundary_id,
                arch_kind="boundary",
            )
            _geometry(cell, x=x, y=y, w=float(boundary.get("w", 120)), h=float(boundary.get("h", 100)))
            boundary_cells[boundary_id] = cell_id
            unresolved.remove(boundary_id)
            progressed = True
        if not progressed:
            for boundary_id in list(unresolved):
                boundary = boundaries[boundary_id]
                cell_id = f"{prefix}-boundary-{_safe_id(boundary_id)}"
                cell = _cell(root, cell_id=cell_id, value=str(boundary.get("label", boundary_id)), style=_boundary_style(str(boundary.get("kind", "generic"))), parent="1", vertex=True, arch_id=boundary_id, arch_kind="boundary")
                _geometry(cell, x=float(boundary.get("x", 0)), y=float(boundary.get("y", 0)), w=float(boundary.get("w", 120)), h=float(boundary.get("h", 100)))
                boundary_cells[boundary_id] = cell_id
                unresolved.remove(boundary_id)

    node_cells: dict[str, str] = {}
    for placement in view.get("nodes", []):
        if not isinstance(placement, dict):
            continue
        component_id = placement.get("component")
        component = components.get(component_id)
        if not component:
            continue
        boundary_id = placement.get("boundary")
        parent_cell = boundary_cells.get(boundary_id, "1")
        parent_boundary = boundaries.get(boundary_id) if boundary_id else None
        x = float(placement.get("x", 0)) - (float(parent_boundary.get("x", 0)) if parent_boundary else 0)
        y = float(placement.get("y", 0)) - (float(parent_boundary.get("y", 0)) if parent_boundary else 0)
        cell_id = f"{prefix}-component-{_safe_id(component_id)}"
        cell = _cell(
            root,
            cell_id=cell_id,
            value=_node_label(component),
            style=_node_style(component, icons),
            parent=parent_cell,
            vertex=True,
            arch_id=component_id,
            arch_kind="component",
        )
        _geometry(cell, x=x, y=y, w=float(placement.get("w", 160)), h=float(placement.get("h", 90)))
        node_cells[component_id] = cell_id

    for edge_id in view.get("edges", []):
        relationship = relationships.get(edge_id)
        if not relationship:
            continue
        source = node_cells.get(relationship.get("from"))
        target = node_cells.get(relationship.get("to"))
        if not source or not target:
            continue
        cell = _cell(
            root,
            cell_id=f"{prefix}-relationship-{_safe_id(edge_id)}",
            value=_edge_label(relationship),
            style=_edge_style(relationship),
            parent="1",
            edge=True,
            source=source,
            target=target,
            arch_id=edge_id,
            arch_kind="relationship",
        )
        _geometry(cell, relative=True)


def _render_sequence(root: ET.Element, view: dict[str, Any], components: dict[str, dict[str, Any]]) -> None:
    prefix = _safe_id(view["id"])
    participants = [item for item in view.get("participants", []) if item in components]
    width = float(view.get("width", 1600))
    height = float(view.get("height", 900))
    margin = 100.0
    available = max(200.0, width - 2 * margin)
    step = available / max(1, len(participants) - 1)
    x_positions: dict[str, float] = {}
    for index, component_id in enumerate(participants):
        component = components[component_id]
        x = margin + index * step
        x_positions[component_id] = x
        colors = KIND_STYLES.get(component.get("kind", "generic"), KIND_STYLES["generic"])
        header = _cell(
            root,
            cell_id=f"{prefix}-participant-{_safe_id(component_id)}",
            value=_node_label(component),
            style=(
                "html=1;whiteSpace=wrap;rounded=1;arcSize=10;shadow=0;align=center;verticalAlign=middle;"
                f"fillColor={colors['fill']};strokeColor={colors['stroke']};fontColor={colors['font']};"
                "strokeWidth=1.5;fontFamily=Helvetica;fontSize=11;"
            ),
            vertex=True,
            arch_id=component_id,
            arch_kind="component",
        )
        _geometry(header, x=x - 75, y=95, w=150, h=64)
        top_id = f"{prefix}-life-top-{_safe_id(component_id)}"
        bottom_id = f"{prefix}-life-bottom-{_safe_id(component_id)}"
        top = _cell(root, cell_id=top_id, style="opacity=0;fillOpacity=0;strokeOpacity=0;", vertex=True)
        bottom = _cell(root, cell_id=bottom_id, style="opacity=0;fillOpacity=0;strokeOpacity=0;", vertex=True)
        _geometry(top, x=x, y=160, w=1, h=1)
        _geometry(bottom, x=x, y=height - 70, w=1, h=1)
        life = _cell(root, cell_id=f"{prefix}-lifeline-{_safe_id(component_id)}", style="edgeStyle=none;html=1;dashed=1;dashPattern=4 4;strokeColor=#98A2B3;endArrow=none;startArrow=none;", edge=True, source=top_id, target=bottom_id)
        _geometry(life, relative=True)

    row_y = 205.0
    row_gap = max(38.0, min(60.0, (height - 300.0) / max(1, len(view.get("interactions", [])))))
    for index, interaction in enumerate(view.get("interactions", []), start=1):
        if not isinstance(interaction, dict):
            continue
        source_id = interaction.get("from")
        target_id = interaction.get("to")
        if source_id not in x_positions or target_id not in x_positions:
            continue
        y = row_y + (index - 1) * row_gap
        source_anchor = f"{prefix}-msg-{index}-source"
        target_anchor = f"{prefix}-msg-{index}-target"
        source = _cell(root, cell_id=source_anchor, style="opacity=0;fillOpacity=0;strokeOpacity=0;", vertex=True)
        target = _cell(root, cell_id=target_anchor, style="opacity=0;fillOpacity=0;strokeOpacity=0;", vertex=True)
        _geometry(source, x=x_positions[source_id], y=y, w=1, h=1)
        _geometry(target, x=x_positions[target_id], y=y, w=1, h=1)
        kind = interaction.get("kind", "sync")
        style = EDGE_STYLES.get(kind, EDGE_STYLES["sync"])
        message = _cell(
            root,
            cell_id=f"{prefix}-interaction-{_safe_id(str(interaction.get('id', index)))}",
            value=f"<b>{index}. {interaction.get('label', '')}</b>",
            style=(
                "edgeStyle=none;html=1;rounded=0;"
                f"strokeColor={style['stroke']};strokeWidth=1.8;dashed={style['dash']};endArrow={style['arrow']};"
                "endFill=1;fontFamily=Helvetica;fontSize=10;fontColor=#344054;labelBackgroundColor=#FFFFFF;"
            ),
            edge=True,
            source=source_anchor,
            target=target_anchor,
            arch_id=str(interaction.get("id", f"interaction-{index}")),
            arch_kind="interaction",
        )
        _geometry(message, relative=True)
        if interaction.get("note"):
            note = _cell(root, cell_id=f"{prefix}-interaction-note-{index}", value=str(interaction["note"]), style="shape=note;whiteSpace=wrap;html=1;backgroundOutline=1;size=12;fillColor=#FFFAEB;strokeColor=#F79009;fontColor=#7A2E0E;fontSize=9;", vertex=True)
            _geometry(note, x=min(x_positions[source_id], x_positions[target_id]) + 20, y=y + 10, w=min(240, abs(x_positions[source_id] - x_positions[target_id]) - 30 if abs(x_positions[source_id] - x_positions[target_id]) > 80 else 160), h=34)


def _ui_indexes(ui_spec: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]], dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    screens = {item["id"]: item for item in ui_spec.get("screens", []) if isinstance(item, dict) and item.get("id")}
    components = {item["id"]: item for item in ui_spec.get("components", []) if isinstance(item, dict) and item.get("id")}
    flows = {item["id"]: item for item in ui_spec.get("flows", []) if isinstance(item, dict) and item.get("id")}
    personas = {item["id"]: item for item in ui_spec.get("personas", []) if isinstance(item, dict) and item.get("id")}
    return screens, components, flows, personas


def _render_ui_wireframe(root: ET.Element, view: dict[str, Any], ui_spec: dict[str, Any]) -> None:
    screens, ui_components, _flows, _personas = _ui_indexes(ui_spec)
    screen = screens.get(view.get("screen"), {})
    breakpoint_id = view.get("breakpoint")
    layout = next((item for item in screen.get("layouts", []) if isinstance(item, dict) and item.get("breakpoint") == breakpoint_id), {})
    regions = {item["id"]: item for item in screen.get("regions", []) if isinstance(item, dict) and item.get("id")}
    states = {item["id"]: item for item in screen.get("states", []) if isinstance(item, dict) and item.get("id")}
    state = states.get(view.get("state")) or next((item for item in states.values() if item.get("kind") == "default"), {})
    prefix = _safe_id(view["id"])
    view_width = float(view.get("width", 1600))
    view_height = float(view.get("height", 900))
    source_width = max(240.0, float(layout.get("width", 1280)))
    source_height = max(320.0, float(layout.get("height", 720)))
    max_width = max(400.0, view_width - 390.0)
    max_height = max(300.0, view_height - 180.0)
    scale = min(max_width / source_width, max_height / source_height)
    frame_width = source_width * scale
    frame_height = source_height * scale
    origin_x = 42.0
    origin_y = 108.0
    chrome_height = 34.0

    frame = _cell(
        root,
        cell_id=f"{prefix}-ui-frame",
        value="",
        style="rounded=1;arcSize=10;html=1;fillColor=#FFFFFF;strokeColor=#667085;strokeWidth=2;shadow=0;",
        vertex=True,
        arch_id=str(screen.get("id", "screen")),
        arch_kind="ui-screen",
    )
    _geometry(frame, x=origin_x, y=origin_y, w=frame_width, h=frame_height + chrome_height)
    chrome = _cell(
        root,
        cell_id=f"{prefix}-ui-chrome",
        value=f"●  ●  ●&nbsp;&nbsp;&nbsp; <b>{screen.get('route', '/')}</b>&nbsp;&nbsp; · &nbsp;{breakpoint_id}",
        style="rounded=1;arcSize=10;html=1;fillColor=#F2F4F7;strokeColor=#667085;strokeWidth=1;align=left;verticalAlign=middle;fontColor=#475467;fontSize=10;spacingLeft=10;",
        vertex=True,
    )
    _geometry(chrome, x=origin_x, y=origin_y, w=frame_width, h=chrome_height)

    for placement in layout.get("placements", []):
        if not isinstance(placement, dict):
            continue
        region_id = placement.get("region")
        region = regions.get(region_id)
        if not region:
            continue
        component = ui_components.get(region.get("component"), {})
        actions = [item.get("label", "Action") for item in region.get("actions", []) if isinstance(item, dict)]
        bindings = region.get("bindings", [])
        meta = " · ".join(filter(None, [str(component.get("name", region.get("component", ""))), str(region.get("role", ""))]))
        action_text = f'<br><span style="font-size:9px;color:#175CD3">Actions: {" / ".join(actions)}</span>' if actions else ""
        binding_text = f'<br><span style="font-size:9px;color:#B54708">Bindings: {", ".join(bindings)}</span>' if bindings else ""
        value = f'<b>{region.get("name", region_id)}</b><br><span style="font-size:9px;color:#667085">{meta}</span><br><span style="font-size:9px;color:#475467">{region.get("description", "")}</span>{action_text}{binding_text}'
        role = str(region.get("role", "region")).lower()
        fill = "#F9FAFB"
        stroke = "#98A2B3"
        if role in {"main", "form", "article"}:
            fill, stroke = "#EFF8FF", "#2E90FA"
        elif role in {"navigation", "banner", "complementary"}:
            fill, stroke = "#F4F3FF", "#7A5AF8"
        elif actions:
            fill, stroke = "#ECFDF3", "#12B76A"
        cell = _cell(
            root,
            cell_id=f"{prefix}-ui-region-{_safe_id(str(region_id))}",
            value=value,
            style=(
                "rounded=1;arcSize=8;html=1;whiteSpace=wrap;shadow=0;align=left;verticalAlign=top;spacing=8;"
                f"fillColor={fill};strokeColor={stroke};strokeWidth=1.5;fontColor=#101828;fontSize=11;"
            ),
            vertex=True,
            arch_id=f"{screen.get('id', 'screen')}.{region_id}",
            arch_kind="ui-region",
        )
        _geometry(
            cell,
            x=origin_x + float(placement.get("x", 0)) * scale,
            y=origin_y + chrome_height + float(placement.get("y", 0)) * scale,
            w=float(placement.get("w", 80)) * scale,
            h=float(placement.get("h", 50)) * scale,
        )

    if state:
        state_box = _cell(
            root,
            cell_id=f"{prefix}-ui-state",
            value=(
                f'<b>Rendered state · {state.get("name", state.get("id", "default"))}</b><br>'
                f'<span style="font-size:9px;color:#667085">{state.get("kind", "")} · trigger: {state.get("trigger", "")}</span><br>'
                f'<span style="font-size:9px;color:#475467">{state.get("content", "")}</span><br>'
                f'<span style="font-size:9px;color:#175CD3">Focus: {state.get("focus_target", "")} · Announces: {state.get("announcement", "")}</span>'
            ),
            style="shape=note;whiteSpace=wrap;html=1;backgroundOutline=1;size=14;fillColor=#FFFAEB;strokeColor=#F79009;fontColor=#7A2E0E;fontSize=10;align=left;verticalAlign=top;spacing=8;",
            vertex=True,
            arch_id=f"{screen.get('id', 'screen')}.{state.get('id', 'state')}",
            arch_kind="ui-state",
        )
        _geometry(state_box, x=view_width - 340, y=108, w=310, h=128)


def _render_user_flow(root: ET.Element, view: dict[str, Any], ui_spec: dict[str, Any]) -> None:
    screens, _components, flows, personas = _ui_indexes(ui_spec)
    flow = flows.get(view.get("flow"), {})
    persona = personas.get(flow.get("actor"), {})
    prefix = _safe_id(view["id"])
    width = float(view.get("width", 1600))
    steps = [item for item in flow.get("steps", []) if isinstance(item, dict)]
    actor = _cell(
        root,
        cell_id=f"{prefix}-flow-persona",
        value=f'<b>{persona.get("name", flow.get("actor", "Persona"))}</b><br><span style="font-size:9px;color:#475467">Goal: {flow.get("goal", "")}</span>',
        style="shape=mxgraph.basic.person;html=1;whiteSpace=wrap;fillColor=#E8F0FE;strokeColor=#4F6BED;fontColor=#172B4D;fontSize=11;verticalLabelPosition=bottom;verticalAlign=top;align=center;",
        vertex=True,
        arch_id=str(persona.get("id", flow.get("actor", "persona"))),
        arch_kind="ui-persona",
    )
    _geometry(actor, x=52, y=115, w=130, h=110)
    prior_anchor = actor.get("id")
    card_x = 245.0
    card_width = min(430.0, max(300.0, width - 620.0))
    card_height = 106.0
    gap = 34.0
    for index, step in enumerate(steps, start=1):
        y = 105.0 + (index - 1) * (card_height + gap)
        screen = screens.get(step.get("screen"), {})
        alternate = f'<br><span style="font-size:9px;color:#B54708">Exception: {step.get("alternate")}</span>' if step.get("alternate") else ""
        card = _cell(
            root,
            cell_id=f"{prefix}-flow-step-{_safe_id(str(step.get('id', index)))}",
            value=(
                f'<b>{index}. {step.get("action", "")}</b><br>'
                f'<span style="font-size:10px;color:#175CD3">{screen.get("name", step.get("screen", ""))} · {screen.get("route", "")}</span><br>'
                f'<span style="font-size:9px;color:#475467">Outcome: {step.get("outcome", "")}</span>{alternate}'
            ),
            style="rounded=1;arcSize=10;html=1;whiteSpace=wrap;fillColor=#FFFFFF;strokeColor=#2E90FA;strokeWidth=1.5;fontColor=#101828;fontSize=11;align=left;verticalAlign=top;spacing=10;",
            vertex=True,
            arch_id=f"{flow.get('id', 'flow')}.{step.get('id', index)}",
            arch_kind="ui-flow-step",
        )
        _geometry(card, x=card_x, y=y, w=card_width, h=card_height)
        connector = _cell(
            root,
            cell_id=f"{prefix}-flow-edge-{index}",
            value="" if index > 1 else "Start",
            style="edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;strokeColor=#2563EB;strokeWidth=2;endArrow=block;endFill=1;fontColor=#475467;fontSize=9;",
            edge=True,
            source=prior_anchor,
            target=card.get("id"),
        )
        _geometry(connector, relative=True)
        prior_anchor = card.get("id")
    summary = _cell(
        root,
        cell_id=f"{prefix}-flow-summary",
        value=(
            f'<b>Success outcomes</b><br>{"<br>".join("• " + str(item) for item in flow.get("outcomes", [])) or "—"}<br><br>'
            f'<b>Exception paths</b><br>{"<br>".join("• " + str(item) for item in flow.get("exceptions", [])) or "—"}'
        ),
        style="shape=note;whiteSpace=wrap;html=1;backgroundOutline=1;size=14;fillColor=#F0FDF4;strokeColor=#12B76A;fontColor=#05603A;fontSize=10;align=left;verticalAlign=top;spacing=8;",
        vertex=True,
        arch_id=str(flow.get("id", "flow")),
        arch_kind="ui-flow",
    )
    _geometry(summary, x=card_x + card_width + 55, y=105, w=max(260, width - card_x - card_width - 90), h=230)


def _render_ui_state_map(root: ET.Element, view: dict[str, Any], ui_spec: dict[str, Any]) -> None:
    screens, _components, _flows, _personas = _ui_indexes(ui_spec)
    screen = screens.get(view.get("screen"), {})
    states = [item for item in screen.get("states", []) if isinstance(item, dict)]
    prefix = _safe_id(view["id"])
    width = float(view.get("width", 1600))
    columns = 2
    gap = 24.0
    margin = 42.0
    top = 105.0
    card_width = (width - margin * 2 - gap) / columns
    card_height = 150.0
    for index, state in enumerate(states):
        column = index % columns
        row = index // columns
        x = margin + column * (card_width + gap)
        y = top + row * (card_height + gap)
        actions = ", ".join(state.get("available_actions", [])) or "None"
        card = _cell(
            root,
            cell_id=f"{prefix}-state-{_safe_id(str(state.get('id', index)))}",
            value=(
                f'<b>{state.get("name", state.get("id", "State"))}</b> '
                f'<span style="font-size:9px;color:#667085">({state.get("kind", "")})</span><br>'
                f'<span style="font-size:9px;color:#475467">Trigger: {state.get("trigger", "")}</span><br>'
                f'{state.get("content", "")}<br>'
                f'<span style="font-size:9px;color:#175CD3">Actions: {actions}<br>Focus: {state.get("focus_target", "")}<br>Announcement: {state.get("announcement", "")}</span>'
            ),
            style="rounded=1;arcSize=8;html=1;whiteSpace=wrap;fillColor=#FFFFFF;strokeColor=#7A5AF8;strokeWidth=1.5;fontColor=#101828;fontSize=11;align=left;verticalAlign=top;spacing=10;",
            vertex=True,
            arch_id=f"{screen.get('id', 'screen')}.{state.get('id', index)}",
            arch_kind="ui-state",
        )
        _geometry(card, x=x, y=y, w=card_width, h=card_height)


def _render_legend(
    root: ET.Element,
    view: dict[str, Any],
    components: dict[str, dict[str, Any]],
    relationships: dict[str, dict[str, Any]],
) -> None:
    legend = view.get("legend", {})
    if not isinstance(legend, dict) or legend.get("mode") == "hidden":
        return
    entries: list[tuple[str, str, str]] = []
    if legend.get("mode") == "authored":
        for entry in legend.get("entries", []):
            if isinstance(entry, dict):
                entries.append((str(entry.get("label", "Symbol")), str(entry.get("description", "")), str(entry.get("color", "#667085"))))
    else:
        if view.get("type") == "sequence":
            entries.extend(
                [
                    ("Solid arrow", "Synchronous request or response", EDGE_STYLES["sync"]["stroke"]),
                    ("Dashed arrow", "Async message or return", EDGE_STYLES["async"]["stroke"]),
                ]
            )
        elif view.get("type") == "ui-wireframe":
            entries.extend(
                [
                    ("Blue region", "Primary content or data-bound surface", "#2E90FA"),
                    ("Green region", "Interactive action surface", "#12B76A"),
                    ("Purple region", "Navigation or supporting landmark", "#7A5AF8"),
                    ("State note", "Rendered state, focus, and announcement", "#F79009"),
                ]
            )
        elif view.get("type") == "user-flow":
            entries.extend(
                [
                    ("Persona", "User or role pursuing the goal", "#4F6BED"),
                    ("Step", "Action on a named screen with observable outcome", "#2E90FA"),
                    ("Exception", "Alternate or failure path", "#B54708"),
                ]
            )
        elif view.get("type") == "ui-state-map":
            entries.extend(
                [
                    ("State card", "Trigger, content, actions, focus, and announcement", "#7A5AF8"),
                    ("No motion", "All transitions are static by contract", "#667085"),
                ]
            )
        else:
            kind_ids = []
            for placement in view.get("nodes", []):
                component = components.get(placement.get("component"), {}) if isinstance(placement, dict) else {}
                kind = component.get("kind", "generic")
                if kind not in kind_ids:
                    kind_ids.append(kind)
            for kind in kind_ids[:6]:
                colors = KIND_STYLES.get(kind, KIND_STYLES["generic"])
                entries.append((kind.replace("-", " ").title(), "Component type", colors["stroke"]))
            modes = []
            for edge_id in view.get("edges", []):
                mode = relationships.get(edge_id, {}).get("mode", "sync")
                if mode not in modes:
                    modes.append(mode)
            for mode in modes[:4]:
                entries.append((f"{mode.title()} flow", "Connection mode", EDGE_STYLES.get(mode, EDGE_STYLES["sync"])["stroke"]))
    if not entries:
        return
    width = 310.0
    row = 25.0
    height = 40.0 + row * len(entries)
    x = float(legend.get("x", float(view.get("width", 1600)) - width - 28))
    y = float(legend.get("y", float(view.get("height", 900)) - height - 28))
    prefix = _safe_id(view["id"])
    box = _cell(root, cell_id=f"{prefix}-legend-box", value="<b>Legend</b>", style="swimlane;html=1;rounded=1;horizontal=1;startSize=28;collapsible=0;container=0;fillColor=#FFFFFF;swimlaneFillColor=#FFFFFF;strokeColor=#98A2B3;fontColor=#344054;fontSize=11;fontStyle=1;align=left;spacingLeft=8;", vertex=True, arch_id=f"{view['id']}-legend", arch_kind="legend")
    _geometry(box, x=x, y=y, w=width, h=height)
    for index, (label, description, color) in enumerate(entries):
        item = _cell(root, cell_id=f"{prefix}-legend-item-{index}", value=f'<b>{label}</b> <span style="font-size:9px;color:#667085">— {description}</span>', style=f"text;html=1;align=left;verticalAlign=middle;whiteSpace=wrap;fillColor=none;strokeColor=none;fontColor=#344054;fontSize=9;spacingLeft=20;indicatorColor={color};indicatorShape=rect;", vertex=True)
        _geometry(item, x=x + 8, y=y + 31 + index * row, w=width - 16, h=row - 2)
