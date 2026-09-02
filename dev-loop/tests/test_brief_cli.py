from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cli  # noqa: E402
from progress import record  # noqa: E402


class BriefCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["DEVLOOP_HOME"] = self.tmp.name

    def tearDown(self) -> None:
        os.environ.pop("DEVLOOP_HOME", None)
        self.tmp.cleanup()

    def test_given_no_args_when_main_then_home_brief(self) -> None:
        from io import StringIO
        from contextlib import redirect_stdout

        buf = StringIO()
        with redirect_stdout(buf):
            rc = cli.main([])
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn("description: Jira-to-PR conductor", out)
        self.assertIn("help[", out)

    def test_given_progress_when_brief_then_not_markdown_table(self) -> None:
        from io import StringIO
        from contextlib import redirect_stdout
        from paths import run_dir

        run = run_dir("LCN-7")
        record(run, "spec", "waiting_approval", ticket="LCN-7")
        buf = StringIO()
        with redirect_stdout(buf):
            rc = cli.main(["progress", "LCN-7"])
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn("now: spec / waiting_approval", out)
        self.assertNotIn("| time (UTC) |", out)

    def test_given_progress_full_when_main_then_markdown(self) -> None:
        from io import StringIO
        from contextlib import redirect_stdout
        from paths import run_dir

        run = run_dir("LCN-8")
        record(run, "spec", "ok", ticket="LCN-8")
        buf = StringIO()
        with redirect_stdout(buf):
            rc = cli.main(["--full", "progress", "LCN-8"])
        self.assertEqual(rc, 0)
        self.assertIn("# LCN-8", buf.getvalue())

    def test_given_status_json_when_main_then_parseable(self) -> None:
        from io import StringIO
        from contextlib import redirect_stdout

        buf = StringIO()
        with redirect_stdout(buf):
            rc = cli.main(["--format", "json", "status"])
        self.assertEqual(rc, 0)
        data = json.loads(buf.getvalue())
        self.assertIn("meta", data)
        self.assertIn("help", data)

    def test_given_unknown_flag_when_parse_then_exits(self) -> None:
        with self.assertRaises(SystemExit):
            cli.build_parser().parse_args(["status", "--nope"])

    def test_given_step_args_when_parse_then_cmd_step(self) -> None:
        ns = cli.build_parser().parse_args(["step", "ASE-9", "--repo", "/tmp/lab"])
        self.assertEqual(ns.cmd, "step")
        self.assertEqual(ns.key, "ASE-9")
        self.assertEqual(ns.repo, "/tmp/lab")


if __name__ == "__main__":
    unittest.main()
