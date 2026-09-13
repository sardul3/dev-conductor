from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from urllib.request import Request

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import DevLoopConfig
from jira_client import jira_request
from jira_workflow import comment_payload, find_transition_id, pr_comment_text, progress, transition_payload


class FakeResp:
    def __init__(self, payload: dict | None, status: int = 200) -> None:
        self._payload = json.dumps(payload).encode() if payload is not None else b""
        self.status = status

    def read(self) -> bytes:
        return self._payload

    def __enter__(self) -> FakeResp:
        return self

    def __exit__(self, *args: object) -> None:
        return None


class JiraWorkflowTests(unittest.TestCase):
    def test_given_transitions_when_find_by_name_then_id(self) -> None:
        data = {
            "transitions": [
                {"id": "11", "name": "In Progress"},
                {"id": "21", "name": "In Review"},
            ]
        }
        self.assertEqual(find_transition_id(data, "in review"), "21")
        self.assertIsNone(find_transition_id(data, "Done"))

    def test_given_text_when_comment_payload_then_adf_doc(self) -> None:
        body = comment_payload("shipped ASE-1")
        self.assertEqual(body["body"]["type"], "doc")
        text = body["body"]["content"][0]["content"][0]["text"]
        self.assertEqual(text, "shipped ASE-1")

    def test_given_id_when_transition_payload_then_nested_id(self) -> None:
        self.assertEqual(transition_payload("21"), {"transition": {"id": "21"}})

    def test_given_post_when_jira_request_then_sends_json_body(self) -> None:
        captured: list[Request] = []

        def urlopen(req: Request, timeout: int = 0) -> FakeResp:
            captured.append(req)
            return FakeResp({"ok": True})

        jira_request(
            "https://ex.atlassian.net",
            "a@b.com",
            "tok",
            "/rest/api/3/issue/ASE-1/comment",
            method="POST",
            payload={"body": {"type": "doc"}},
            urlopen=urlopen,
        )
        req = captured[0]
        self.assertEqual(req.get_method(), "POST")
        self.assertIn(b'"type": "doc"', req.data or b"")
        ctype = req.headers.get("Content-type") or req.headers.get("Content-Type") or ""
        self.assertIn("application/json", ctype)

    def test_given_non_issue_key_when_progress_then_skips_jira(self) -> None:
        from io import StringIO
        from contextlib import redirect_stdout
        from unittest.mock import patch

        cfg = DevLoopConfig()
        buf = StringIO()
        with (
            patch("jira_workflow.jira_request", side_effect=AssertionError("no jira")),
            patch("jira_workflow.jira_creds", return_value=("https://ex.atlassian.net", "a@b.com", "tok")),
            redirect_stdout(buf),
        ):
            result = progress(cfg, "tmpg9ippqmj", "on_block", "budget")
        self.assertEqual(result["status"], "skipped")
        self.assertIn("bad key", result["note"])
        self.assertIn("skipped", buf.getvalue())

    def test_given_workflow_disabled_when_progress_then_skipped_not_silent(self) -> None:
        from io import StringIO
        from contextlib import redirect_stdout

        cfg = DevLoopConfig()
        cfg.workflow.enabled = False
        buf = StringIO()
        with redirect_stdout(buf):
            result = progress(cfg, "LCN-2", "on_start", "dev-loop started")
        self.assertEqual(result["status"], "skipped")
        self.assertIn("workflow.enabled is false", result["note"])
        self.assertIn("jira on_start skipped", buf.getvalue())

    def test_given_on_start_when_unassigned_then_puts_assignee(self) -> None:
        from unittest.mock import patch

        cfg = DevLoopConfig()
        calls: list[tuple[str, str, dict | None]] = []

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
            calls.append((method, path, payload))
            if path.endswith("/myself"):
                return {"accountId": "acc-me", "displayName": "Sagar", "emailAddress": "a@b.com"}
            if path.endswith("/transitions") and method == "GET":
                return {"transitions": [{"id": "11", "name": "In Progress"}]}
            if path.endswith("/LCN-2") and method == "GET":
                return {"fields": {"assignee": None, "comment": {"comments": []}}}
            return {}

        with (
            patch("jira_workflow.jira_creds", return_value=("https://ex.atlassian.net", "a@b.com", "tok")),
            patch("jira_workflow.jira_request", side_effect=fake_request),
        ):
            result = progress(cfg, "LCN-2", "on_start", "dev-loop started")

        self.assertEqual(result["status"], "ok")
        self.assertTrue(
            any(m == "PUT" and p.endswith("/issue/LCN-2/assignee") and (pl or {}).get("accountId") == "acc-me" for m, p, pl in calls),
            f"missing assignee PUT: {calls}",
        )
        self.assertTrue(any(m == "GET" and p.endswith("/myself") for m, p, _ in calls))

    def test_given_on_start_when_other_assignee_then_skips_assign(self) -> None:
        from io import StringIO
        from contextlib import redirect_stdout
        from unittest.mock import patch

        cfg = DevLoopConfig()
        calls: list[tuple[str, str, dict | None]] = []

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
            calls.append((method, path, payload))
            if path.endswith("/myself"):
                return {"accountId": "acc-me", "displayName": "Sagar"}
            if path.endswith("/transitions") and method == "GET":
                return {"transitions": [{"id": "11", "name": "In Progress"}]}
            if path.endswith("/LCN-2") and method == "GET":
                return {
                    "fields": {
                        "assignee": {"accountId": "acc-other", "displayName": "Alex"},
                        "comment": {"comments": []},
                    }
                }
            return {}

        buf = StringIO()
        with (
            patch("jira_workflow.jira_creds", return_value=("https://ex.atlassian.net", "a@b.com", "tok")),
            patch("jira_workflow.jira_request", side_effect=fake_request),
            redirect_stdout(buf),
        ):
            result = progress(cfg, "LCN-2", "on_start", "dev-loop started")

        self.assertEqual(result["status"], "ok")
        self.assertFalse(any(m == "PUT" and p.endswith("/assignee") for m, p, _ in calls), calls)
        self.assertIn("jira assign skipped (already Alex)", buf.getvalue())

    def test_given_on_start_when_already_self_then_assign_noop(self) -> None:
        from unittest.mock import patch

        cfg = DevLoopConfig()
        calls: list[tuple[str, str, dict | None]] = []

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
            calls.append((method, path, payload))
            if path.endswith("/myself"):
                return {"accountId": "acc-me", "displayName": "Sagar"}
            if path.endswith("/transitions") and method == "GET":
                return {"transitions": [{"id": "11", "name": "In Progress"}]}
            if path.endswith("/LCN-2") and method == "GET":
                return {
                    "fields": {
                        "assignee": {"accountId": "acc-me", "displayName": "Sagar"},
                        "comment": {"comments": []},
                    }
                }
            return {}

        with (
            patch("jira_workflow.jira_creds", return_value=("https://ex.atlassian.net", "a@b.com", "tok")),
            patch("jira_workflow.jira_request", side_effect=fake_request),
        ):
            result = progress(cfg, "LCN-2", "on_start", "dev-loop started")

        self.assertEqual(result["status"], "ok")
        self.assertFalse(any(m == "PUT" and p.endswith("/assignee") for m, p, _ in calls), calls)

    def test_given_started_comment_when_on_start_then_skips_duplicate_comment(self) -> None:
        from unittest.mock import patch

        cfg = DevLoopConfig()
        calls: list[tuple[str, str, dict | None]] = []

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
            calls.append((method, path, payload))
            if path.endswith("/myself"):
                return {"accountId": "acc-me", "displayName": "Sagar"}
            if path.endswith("/transitions") and method == "GET":
                return {"transitions": [{"id": "11", "name": "In Progress"}]}
            if path.endswith("/LCN-2") and method == "GET":
                return {
                    "fields": {
                        "assignee": None,
                        "comment": {
                            "comments": [
                                {
                                    "body": {
                                        "type": "doc",
                                        "content": [
                                            {
                                                "type": "paragraph",
                                                "content": [
                                                    {"type": "text", "text": "dev-loop started in lucene"}
                                                ],
                                            }
                                        ],
                                    }
                                }
                            ]
                        },
                    }
                }
            return {}

        with (
            patch("jira_workflow.jira_creds", return_value=("https://ex.atlassian.net", "a@b.com", "tok")),
            patch("jira_workflow.jira_request", side_effect=fake_request),
        ):
            result = progress(cfg, "LCN-2", "on_start", "dev-loop started in lucene")

        self.assertEqual(result["status"], "ok")
        self.assertFalse(any(m == "POST" and p.endswith("/comment") for m, p, _ in calls), calls)
        self.assertTrue(any(m == "PUT" and p.endswith("/assignee") for m, p, _ in calls), calls)

    def test_given_opened_pr_when_on_pr_comment_then_includes_https_url(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            subprocess.check_call(["git", "init"], cwd=repo, stdout=subprocess.DEVNULL)
            subprocess.check_call(
                ["git", "remote", "add", "origin", "git@github.com:owner/repo.git"],
                cwd=repo,
            )
            text = pr_comment_text(
                DevLoopConfig(),
                1,
                "feat/LCN-2-aita-001-initialize-python-project",
                repo=repo,
            )
        self.assertIn("https://github.com/owner/repo/pull/1", text)
        self.assertIn("https://", text)
        self.assertIn("#1", text)
        self.assertIn("feat/LCN-2-aita-001-initialize-python-project", text)

    def test_given_short_template_when_on_pr_comment_then_still_includes_url(self) -> None:
        cfg = DevLoopConfig()
        cfg.workflow.on_pr_comment = "PR #{number} opened on {branch}"
        text = pr_comment_text(
            cfg,
            12,
            "feat/ASE-12-health",
            url="https://github.com/org/app/pull/12",
        )
        self.assertIn("https://github.com/org/app/pull/12", text)
        self.assertIn("feat/ASE-12-health", text)
