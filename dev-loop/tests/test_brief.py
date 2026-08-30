from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from brief import Connector, Document, clip, emit, encode_table, fail  # noqa: E402


class DummyPort(Connector):
    name = "dummy"
    description = "Example port"
    table_name = "items"
    columns = ("id", "title", "state")
    help = ("Run `cli.py dummy view <id>`",)

    def fetch(self, **kwargs):
        return {"items": kwargs.get("items") or []}


class BriefTests(unittest.TestCase):
    def test_given_rows_when_encode_table_then_toon_header_and_cells(self) -> None:
        lines = encode_table(
            "issues",
            ["number", "title", "state"],
            [{"number": 42, "title": "Fix login", "state": "open"}],
        )
        self.assertEqual(lines[0], "issues[1]{number,title,state}:")
        self.assertIn("42,Fix login,open", lines[1])

    def test_given_long_text_when_clip_then_size_hint(self) -> None:
        out = clip("x" * 200, limit=20, full=False)
        self.assertTrue(out.startswith("x" * 20))
        self.assertIn("200 chars", out)
        self.assertIn("--full", out)
        self.assertEqual(clip("x" * 200, limit=20, full=True), "x" * 200)

    def test_given_empty_rows_when_emit_then_zero_results(self) -> None:
        doc = Document(
            bin="cli.py",
            description="list tickets",
            tables={"tickets": (["key"], [])},
            help=["Run `cli.py start <key>`"],
        )
        text = emit(doc)
        self.assertIn("tickets[0]{key}:", text)
        self.assertIn("empty: 0 results", text)
        self.assertIn("help[1]:", text)
        self.assertIn("cli.py start", text)

    def test_given_json_format_when_emit_then_parseable_and_clipped(self) -> None:
        doc = Document(
            bin="cli.py",
            description="d",
            meta={"summary": "a" * 80},
            tables={"items": (["id"], [{"id": "1"}])},
        )
        data = json.loads(emit(doc, fmt="json", clip_at=10))
        self.assertEqual(data["count"], 1)
        self.assertIn("truncated", data["meta"]["summary"])

    def test_given_connector_when_view_then_principles_applied(self) -> None:
        text = DummyPort().view(items=[{"id": "A", "title": "One", "state": "open", "secret": "nope"}])
        self.assertIn("bin:", text)
        self.assertIn("description: Example port", text)
        self.assertIn("items[1]{id,title,state}:", text)
        self.assertNotIn("secret", text)
        self.assertIn("help[1]:", text)
        self.assertIn("count: 1", text)

    def test_given_fail_when_print_then_error_on_stdout(self) -> None:
        import io
        from contextlib import redirect_stdout

        buf = io.StringIO()
        with redirect_stdout(buf):
            code = fail("no ticket")
        self.assertEqual(code, 1)
        self.assertIn("error: no ticket", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
