from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from progress import current, record, render_progress


class ProgressTests(unittest.TestCase):
    def test_given_events_when_record_then_current_is_last_stage(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run = Path(td)
            record(run, "fetch", "ok", note="LCN-2")
            record(run, "spec", "waiting_approval", artifact="spec.md")
            data = json.loads((run / "status.json").read_text(encoding="utf-8"))
            self.assertEqual(data["current"]["stage"], "spec")
            self.assertEqual(data["current"]["status"], "waiting_approval")
            self.assertEqual(len(data["history"]), 2)
            self.assertEqual(current(run)["stage"], "spec")
            md = (run / "progress.md").read_text(encoding="utf-8")
            self.assertIn("**Now:** spec / waiting_approval", md)
            self.assertNotIn("STAGE_DONE", md)

    def test_given_history_when_render_then_names_the_gate(self) -> None:
        md = render_progress(
            "LCN-2",
            {"stage": "spec", "status": "waiting_approval"},
            [{"stage": "spec", "status": "waiting_approval", "note": "human gate"}],
        )
        self.assertIn("spec / waiting_approval", md)
        self.assertIn("human gate", md)

    def test_given_old_handshake_when_backfill_then_names_spec_gate(self) -> None:
        from progress import backfill

        with tempfile.TemporaryDirectory() as td:
            run = Path(td) / "LCN-2"
            run.mkdir()
            (run / "issue.md").write_text("x", encoding="utf-8")
            (run / "spec.md").write_text("y", encoding="utf-8")
            (run / "APPROVED").write_text("", encoding="utf-8")
            (run / "STAGE_DONE").write_text("", encoding="utf-8")
            data = backfill(run)
            self.assertEqual(data["current"]["stage"], "spec")
            self.assertEqual(data["current"]["status"], "approved")
            self.assertTrue((run / "SPEC_APPROVED").is_file())
            self.assertIn("spec only", (run / "progress.md").read_text(encoding="utf-8"))
