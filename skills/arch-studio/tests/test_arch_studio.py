from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

from archstudio.builder import build_bundle  # noqa: E402
from archstudio.drawio import load_icons  # noqa: E402
from archstudio.model import all_findings, finding_summary, load_model  # noqa: E402
from archstudio.reports import semantic_diff  # noqa: E402


class ArchStudioUiSpecificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.model_path = SKILL_ROOT / "examples" / "retail-order-integration.arch.json"
        cls.model = load_model(cls.model_path)
        cls.icons = load_icons(SKILL_ROOT / "assets" / "azure-icons.json")

    def findings(self, model: dict) -> list:
        return all_findings(model, set(self.icons))

    def test_reference_model_passes_strict_gate(self) -> None:
        findings = self.findings(self.model)
        self.assertEqual("pass", finding_summary(findings)["status"])
        self.assertFalse([item for item in findings if item.blocking])

    def test_strict_build_contains_ui_handoff_and_review_objects(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = build_bundle(self.model, directory, SKILL_ROOT, strict=True, generator_version="test")
            names = {path.name for path in result.files}
            self.assertTrue(
                {
                    "retail-order-integration.drawio",
                    "review.html",
                    "ui-specification.md",
                    "ui-component-matrix.csv",
                    "ui-acceptance-plan.md",
                    "design-tokens.json",
                    "traceability.csv",
                    "build-receipt.json",
                }.issubset(names)
            )
            review = (Path(directory) / "review.html").read_text(encoding="utf-8")
            for marker in ("ui-screen:ui-screen-order-entry", "ui-action:ui-screen-order-entry.ui-action-submit-order", "ui-state:ui-screen-order-entry.ui-state-error", "ui-flow-step:ui-flow-submit-order.ui-step-submit-order"):
                self.assertIn(marker, review)
            self.assertNotIn("@keyframes", review)
            self.assertNotIn("animation:", review)
            tokens = json.loads((Path(directory) / "design-tokens.json").read_text(encoding="utf-8"))
            self.assertFalse(tokens["motion"]["enabled"])

    def test_drawio_contains_editable_ui_pages_and_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            build_bundle(self.model, directory, SKILL_ROOT, strict=True, generator_version="test")
            root = ET.parse(Path(directory) / "retail-order-integration.drawio").getroot()
            self.assertEqual(len(self.model["views"]), len(root.findall("diagram")))
            names = {item.get("name") for item in root.findall("diagram")}
            self.assertIn("Order entry · compact responsive wireframe", names)
            self.assertIn("Order entry screen-state contract", names)
            kinds = {cell.get("arch-kind") for cell in root.iter("mxCell") if cell.get("arch-kind")}
            self.assertTrue({"ui-screen", "ui-region", "ui-state", "ui-flow-step"}.issubset(kinds))

    def test_data_bound_screen_requires_loading_empty_and_error_states(self) -> None:
        candidate = copy.deepcopy(self.model)
        screen = candidate["ui_spec"]["screens"][0]
        screen["states"] = [state for state in screen["states"] if state["kind"] != "error"]
        blockers = [item for item in self.findings(candidate) if item.blocking]
        self.assertTrue(any(item.code == "UI-STATE-COVERAGE" and "error" in item.message for item in blockers))

    def test_binding_must_reach_a_real_architecture_component(self) -> None:
        candidate = copy.deepcopy(self.model)
        candidate["ui_spec"]["bindings"][0]["architecture_component"] = "invented-backend"
        blockers = [item for item in self.findings(candidate) if item.blocking]
        self.assertTrue(any(item.code == "STRUCT-REFERENCE" and "invented-backend" in item.message for item in blockers))

    def test_ui_semantic_and_geometry_diffs_are_separated(self) -> None:
        semantic = copy.deepcopy(self.model)
        semantic["ui_spec"]["components"][0]["description"] = "Changed implementation contract"
        delta = semantic_diff(self.model, semantic)
        changed = delta["collections"]["ui_components"]["changed"]
        self.assertEqual("ui-component-page-header", changed[0]["id"])
        self.assertIn("description", changed[0]["fields"])

        moved = copy.deepcopy(self.model)
        moved["ui_spec"]["screens"][0]["layouts"][0]["placements"][0]["x"] += 1
        movement = semantic_diff(self.model, moved)
        self.assertIn("ui-screen-order-entry", movement["collections"]["ui_screens"]["moved_only"])
        self.assertFalse(movement["collections"]["ui_screens"]["changed"])


if __name__ == "__main__":
    unittest.main()
