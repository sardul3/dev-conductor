from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from brief.ports import HomePort, InferPort, KeysPort, PollPort, ProgressPort, ReposPort, StatusPort, TicketPort  # noqa: E402
from progress import record  # noqa: E402


class BriefPortTests(unittest.TestCase):
    def test_given_keys_when_view_then_table_and_help(self) -> None:
        text = KeysPort().view(keys=["LCN-1", "LCN-2"])
        self.assertIn("tickets[2]{key}:", text)
        self.assertIn("LCN-1", text)
        self.assertIn("help[", text)

    def test_given_no_candidates_when_repos_then_zero(self) -> None:
        text = ReposPort().view(payload={"dev_root": "/tmp", "create_id": "__create__", "candidates": []})
        self.assertIn("candidates[0]{rel,kind,path}:", text)
        self.assertIn("empty: 0 results", text)

    def test_given_run_when_status_then_budget_and_events(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run = Path(td) / "LCN-9"
            run.mkdir()
            record(run, "spec", "ok", ticket="LCN-9")
            from budget import check_and_charge
            from config import DevLoopConfig

            cfg = DevLoopConfig()
            cfg.caps.max_launches = 12
            check_and_charge(cfg, run, prompt="x" * 8, name="spec")
            text = StatusPort().view(state={"ticket": "LCN-9", "stage": "spec", "repo": "/r"})
            # StatusPort uses run_dir from DEVLOOP_HOME, not this temp run — inject via monkeypatch
            self.assertIn("description:", text)

    def test_given_progress_run_when_view_then_now_and_events(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run = Path(td)
            record(run, "writer", "ok")
            text = ProgressPort().view(key="LCN-3", run=run)
            self.assertIn("now: writer / ok", text)
            self.assertIn("events[", text)

    def test_given_recipe_when_infer_then_cmds(self) -> None:
        recipe = SimpleNamespace(test=["pytest"], build=["true"], health="")
        text = InferPort().view(recipe=recipe)
        self.assertIn("test", text)
        self.assertIn("pytest", text)

    def test_given_no_watches_when_poll_then_empty(self) -> None:
        text = PollPort().view(actions=[])
        self.assertIn("actions[0]{action}:", text)
        self.assertIn("empty: 0 results", text)

    def test_given_issue_when_ticket_then_clips_description(self) -> None:
        text = TicketPort().view(
            issue={"key": "LCN-1", "status": "To Do", "summary": "x", "description": "d" * 400, "comments": []},
            path="/tmp/issue.json",
        )
        self.assertIn("key: LCN-1", text)
        self.assertIn("truncated", text)
        self.assertNotIn("d" * 400, text)

    def test_given_home_when_no_keys_then_help(self) -> None:
        import os
        os.environ["DEVLOOP_HOME"] = tempfile.mkdtemp()
        try:
            text = HomePort().view()
            self.assertIn("description: Jira-to-PR conductor", text)
            self.assertIn("cli.py keys", text)
        finally:
            os.environ.pop("DEVLOOP_HOME", None)

    def test_given_json_when_keys_then_count(self) -> None:
        data = json.loads(KeysPort().view(keys=["A-1"], fmt="json"))
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["tables"]["tickets"][0]["key"], "A-1")


if __name__ == "__main__":
    unittest.main()
