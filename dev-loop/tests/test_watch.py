from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from state import update_state
from watch import add_watch, load_watch, remove_watch, save_watch, upsert_watch


class WatchTests(unittest.TestCase):
    def test_given_state_update_when_ticket_changes_then_watch_list_stays(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            watch_path = home / "watch.json"
            state_path = home / "state.json"
            save_watch(
                [{"pr": 7, "repo": "/tmp/app", "key": "LAB-1", "branch": "feat/LAB-1-x"}],
                watch_path,
            )
            update_state(ticket="LAB-2", repo="/tmp/app", path=state_path)
            self.assertEqual(load_watch(watch_path)[0]["pr"], 7)
            self.assertEqual(json.loads(state_path.read_text())["ticket"], "LAB-2")

    def test_given_existing_pr_when_add_watch_then_dedupes(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "watch.json"
            add_watch({"pr": 1, "repo": "/r", "key": "A-1", "branch": "b"}, p)
            add_watch({"pr": 1, "repo": "/r", "key": "A-1", "branch": "b"}, p)
            self.assertEqual(len(load_watch(p)), 1)

    def test_given_watch_when_remove_then_gone(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "watch.json"
            add_watch({"pr": 3, "repo": "/r", "key": "A-1", "branch": "b"}, p)
            remove_watch(3, "/r", p)
            self.assertEqual(load_watch(p), [])

    def test_given_fingerprint_when_upsert_then_updates_same_pr(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "watch.json"
            add_watch({"pr": 9, "repo": "/r", "key": "A-1", "branch": "b"}, p)
            upsert_watch({"pr": 9, "repo": "/r", "key": "A-1", "branch": "b", "last_fp": "abc"}, p)
            self.assertEqual(load_watch(p)[0]["last_fp"], "abc")
