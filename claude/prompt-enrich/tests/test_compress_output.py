#!/usr/bin/env python3
"""RED tests: compress huge test logs via PostToolUse updatedToolOutput."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from compress_output import compress_payload  # noqa: E402


def _bash(command: str, stdout: str) -> dict:
    return {
        "hook_event_name": "PostToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": command},
        "tool_response": {"stdout": stdout, "stderr": "", "output": stdout},
    }


class CompressTests(unittest.TestCase):
    def test_short_output_unchanged(self) -> None:
        out = compress_payload(_bash("pytest -q", "1 passed in 0.01s\n"))
        self.assertIsNone(out)

    def test_huge_pytest_keeps_failures_only(self) -> None:
        lines = ["PASSED tests/test_ok.py::test_a"] * 400
        lines += [
            "FAILED tests/test_pay.py::test_total - AssertionError: 107 != 100",
            "E   AssertionError: expected 107",
            "====== 1 failed, 400 passed in 12.3s ======",
        ]
        blob = "\n".join(lines)
        self.assertGreater(len(blob.splitlines()), 200)
        result = compress_payload(_bash("pytest tests/", blob))
        self.assertIsNotNone(result)
        text = result["hookSpecificOutput"]["updatedToolOutput"]
        self.assertIn("FAILED tests/test_pay.py", text)
        self.assertIn("AssertionError", text)
        self.assertNotIn("PASSED tests/test_ok.py::test_a\nPASSED", text)
        self.assertLess(len(text), len(blob) // 5)

    def test_non_bash_skipped(self) -> None:
        self.assertIsNone(
            compress_payload({"tool_name": "Read", "tool_response": {"content": "x" * 20000}})
        )

    def test_fail_open_empty(self) -> None:
        self.assertIsNone(compress_payload({}))


if __name__ == "__main__":
    unittest.main()
