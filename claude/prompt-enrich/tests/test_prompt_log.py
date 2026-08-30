#!/usr/bin/env python3
"""Tests for prompt-log summarizer (system/tools/messages sizes, redaction)."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from prompt_log import dump_for_disk, redact, should_intercept_session, summarize_body, thin_body, write_capture  # noqa: E402


class PromptLogTests(unittest.TestCase):
    def test_summarize_counts_system_tools_messages(self) -> None:
        body = {
            "model": "OpenRouter/poolside/laguna-s-2.1:free",
            "system": "You are Claude Code. " + ("x" * 200),
            "tools": [
                {"name": "Bash", "description": "run", "input_schema": {"type": "object"}},
                {"name": "Artifact", "input_schema": {"properties": {"pattern": ".*"}}},
            ],
            "messages": [{"role": "user", "content": "make this app prod ready"}],
        }
        s = summarize_body(body)
        self.assertEqual(2, s["tool_count"])
        self.assertEqual(["Bash", "Artifact"], s["tool_names"])
        self.assertGreater(s["system_chars"], 200)
        self.assertEqual(1, s["message_count"])
        self.assertIn("make this app prod ready", s["last_user"])
        self.assertGreater(s["approx_bytes"], 200)

    def test_redact_keys(self) -> None:
        text = 'Authorization: Bearer sk-or-v1-SECRETTOKEN and password=hunter2'
        out = redact(text)
        self.assertNotIn("SECRETTOKEN", out)
        self.assertNotIn("hunter2", out)
        self.assertIn("[redacted]", out)

    def test_system_blocks_list(self) -> None:
        body = {
            "system": [{"type": "text", "text": "alpha"}, {"type": "text", "text": "beta"}],
            "messages": [],
        }
        s = summarize_body(body)
        self.assertEqual("alphabeta", s["system_text"])

    def test_dump_omits_tool_schemas(self) -> None:
        body = {
            "system": "sys",
            "tools": [{"name": "Bash", "description": "run me", "input_schema": {"type": "object", "properties": {"x": {}}}}],
            "messages": [{"role": "user", "content": "hi"}],
        }
        dump = dump_for_disk(body)
        self.assertEqual("sys", dump["system"])
        self.assertNotIn("input_schema", dump["tools"][0])
        self.assertEqual("Bash", dump["tools"][0]["name"])
        self.assertGreater(dump["tools"][0]["schema_bytes"], 0)

    def test_thin_body_is_identity(self) -> None:
        body = {"system": "keep", "messages": []}
        self.assertEqual(body, thin_body(body, enabled=True))

    def test_write_capture_jsonl_and_raw(self) -> None:
        import tempfile

        body = {
            "model": "m",
            "system": "You are Claude Code.",
            "tools": [{"name": "Bash", "input_schema": {"type": "object"}}],
            "messages": [{"role": "user", "content": "hello"}],
        }
        with tempfile.TemporaryDirectory() as tmp:
            result = write_capture(Path(tmp), body)
            self.assertTrue(result["raw"].is_file())
            raw = json.loads(result["raw"].read_text(encoding="utf-8"))
            self.assertIn("You are Claude Code.", raw["system"])
            lines = result["jsonl"].read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(1, len(lines))
            row = json.loads(lines[0])
            self.assertEqual(1, row["tool_count"])
            self.assertEqual("Bash", row["tool_names"][0])

    def test_stock_anthropic_not_intercepted(self) -> None:
        ok, _ = should_intercept_session({}, {})
        self.assertFalse(ok)

    def test_ccr_3456_intercepts_to_same_upstream(self) -> None:
        ok, upstream = should_intercept_session(
            {"ANTHROPIC_BASE_URL": "http://127.0.0.1:3456"},
            {},
        )
        self.assertTrue(ok)
        self.assertEqual("127.0.0.1:3456", upstream)

    def test_already_on_listen_port_upstreams_ccr(self) -> None:
        ok, upstream = should_intercept_session(
            {"ANTHROPIC_BASE_URL": "http://127.0.0.1:3457"},
            {},
        )
        self.assertTrue(ok)
        self.assertEqual("127.0.0.1:3456", upstream)

    def test_disable_skips_intercept(self) -> None:
        ok, _ = should_intercept_session(
            {"PROMPT_LOG_DISABLE": "1", "ANTHROPIC_BASE_URL": "http://127.0.0.1:3456"},
            {},
        )
        self.assertFalse(ok)


if __name__ == "__main__":
    unittest.main()
