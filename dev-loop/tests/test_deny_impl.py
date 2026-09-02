from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from deny_impl import should_deny


class DenyImplTests(unittest.TestCase):
    def test_given_test_writer_when_read_src_main_then_deny(self) -> None:
        payload = {"tool_name": "Read", "tool_input": {"path": "/app/src/main/java/Foo.java"}}
        self.assertTrue(should_deny(payload, "test-writer"))

    def test_given_test_writer_when_read_test_then_allow(self) -> None:
        payload = {"tool_name": "Read", "tool_input": {"path": "/app/src/test/java/FooTest.java"}}
        self.assertFalse(should_deny(payload, "test-writer"))

    def test_given_writer_stage_when_read_src_main_then_allow(self) -> None:
        payload = {"tool_name": "Read", "tool_input": {"path": "/app/src/main/java/Foo.java"}}
        self.assertFalse(should_deny(payload, "writer"))

    def test_given_test_writer_when_glob_star_then_deny(self) -> None:
        payload = {"tool_name": "Glob", "tool_input": {"glob_pattern": "**/*.java"}}
        self.assertTrue(should_deny(payload, "test-writer"))


class CursorDenyTests(unittest.TestCase):
    def test_given_test_writer_read_src_when_cursor_decision_then_deny(self) -> None:
        from deny_impl import cursor_decision

        raw = {"file_path": "/app/src/main/java/Foo.java"}
        out = cursor_decision(raw, "test-writer")
        self.assertEqual(out.get("permission"), "deny")
        self.assertIn("test-writer", out.get("agent_message") or "")

    def test_given_writer_stage_when_cursor_decision_then_allow(self) -> None:
        from deny_impl import cursor_decision

        raw = {"file_path": "/app/src/main/java/Foo.java"}
        out = cursor_decision(raw, "writer")
        self.assertEqual(out.get("permission"), "allow")
