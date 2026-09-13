from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from conductor import require_key, start
from config import DevLoopConfig


_GIT_ENV = {
    **os.environ,
    "GIT_AUTHOR_NAME": "dev-loop-test",
    "GIT_AUTHOR_EMAIL": "dev-loop-test@example.com",
    "GIT_COMMITTER_NAME": "dev-loop-test",
    "GIT_COMMITTER_EMAIL": "dev-loop-test@example.com",
}


def _init_repo(root: Path) -> Path:
    repo = root / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-b", "main", str(repo)], check=True, capture_output=True)
    (repo / "README").write_text("seed\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "README"], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-m", "init"],
        check=True,
        capture_output=True,
        env=_GIT_ENV,
    )
    return repo


class ConductorTests(unittest.TestCase):
    def test_given_bad_key_when_require_key_then_exits(self) -> None:
        with self.assertRaises(SystemExit):
            require_key("not-a-key")

    def test_given_key_when_require_key_then_uppercases(self) -> None:
        self.assertEqual(require_key("ase-12"), "ASE-12")

    def test_given_cursor_start_when_default_workflow_then_fires_on_start(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            repo = _init_repo(root)
            run = root / "runs" / "LCN-99"
            run.mkdir(parents=True)
            cfg = DevLoopConfig()
            cfg.runtime.agent = "cursor"
            cfg.runtime.no_launch = True
            cfg.git.require_github_remote = False
            cfg.git.allow_outside_dev = True
            cfg.git.isolation = "none"
            cfg.jira.auth = "none"
            cfg.jira.base_url = "https://ex.atlassian.net"

            def fake_fetch(key: str, _cfg: DevLoopConfig | None = None) -> Path:
                issue = {
                    "key": key,
                    "summary": "wire jira",
                    "issuetype": "Story",
                    "status": "To Do",
                    "description": "",
                    "comments": [],
                }
                run.mkdir(parents=True, exist_ok=True)
                (run / "issue.json").write_text(json.dumps(issue) + "\n", encoding="utf-8")
                (run / "issue.md").write_text(f"**{key}**\n", encoding="utf-8")
                return run

            calls: list[tuple[str, str]] = []

            def fake_request(
                _base: str,
                _email: str,
                _token: str,
                path: str,
                method: str = "GET",
                payload: dict | None = None,
                query: dict | None = None,
                timeout: int = 20,
                urlopen: object = None,
            ) -> dict:
                calls.append((method, path))
                if path.endswith("/myself"):
                    return {"accountId": "acc-me", "displayName": "Sagar"}
                if path.endswith("/transitions") and method == "GET":
                    return {"transitions": [{"id": "11", "name": "In Progress"}]}
                if path.endswith("/issue/LCN-99") and method == "GET":
                    return {"fields": {"assignee": None, "comment": {"comments": []}}}
                return {}

            with (
                patch("conductor.fetch_issue", side_effect=fake_fetch),
                patch("conductor.load_or_build", return_value=root / "memory"),
                patch("conductor.update_state"),
                patch("jira_workflow.jira_creds", return_value=("https://ex.atlassian.net", "a@b.com", "tok")),
                patch("jira_workflow.jira_request", side_effect=fake_request),
            ):
                start("LCN-99", repo, cfg)

            self.assertTrue(
                any(m == "GET" and p.endswith("/issue/LCN-99/transitions") for m, p in calls),
                f"missing transitions GET: {calls}",
            )
            self.assertTrue(
                any(m == "POST" and p.endswith("/issue/LCN-99/transitions") for m, p in calls),
                f"missing on_start transition POST: {calls}",
            )
            self.assertTrue(
                any(m == "POST" and p.endswith("/issue/LCN-99/comment") for m, p in calls),
                f"missing on_start comment POST: {calls}",
            )
            self.assertTrue(
                any(m == "PUT" and p.endswith("/issue/LCN-99/assignee") for m, p in calls),
                f"missing on_start assignee PUT: {calls}",
            )
            hist = json.loads((run / "status.json").read_text(encoding="utf-8"))["history"]
            jira_ev = [ev for ev in hist if ev.get("stage") == "jira"]
            self.assertTrue(jira_ev, f"start did not record jira event: {hist}")
            self.assertEqual(jira_ev[0]["status"], "ok")
            self.assertIn("on_start", jira_ev[0].get("note") or "")
