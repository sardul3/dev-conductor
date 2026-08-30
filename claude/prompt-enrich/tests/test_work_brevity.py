#!/usr/bin/env python3
"""RED tests: work-session brevity hook; skip grill; back off on depth."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from work_brevity import decide  # noqa: E402


class WorkBrevityTests(unittest.TestCase):
    def test_skip_when_not_work_session(self) -> None:
        self.assertIsNone(decide("implement auth", env={}, turn=1))

    def test_full_contract_turn_one(self) -> None:
        kind = decide("implement auth", env={"PROMPT_ENRICH_WORK_SESSION": "1"}, turn=1)
        self.assertEqual("full", kind)

    def test_short_on_later_turns(self) -> None:
        kind = decide("ok", env={"PROMPT_ENRICH_WORK_SESSION": "1"}, turn=2)
        self.assertEqual("short", kind)

    def test_depth_overrides_brevity(self) -> None:
        kind = decide(
            "explain this thoroughly, walk me through it",
            env={"PROMPT_ENRICH_WORK_SESSION": "1"},
            turn=1,
        )
        self.assertEqual("depth", kind)

    def test_disabled(self) -> None:
        self.assertIsNone(
            decide("x", env={"PROMPT_ENRICH_WORK_SESSION": "1", "TOKEN_EFFICIENCY_OFF": "1"}, turn=1)
        )


if __name__ == "__main__":
    unittest.main()
