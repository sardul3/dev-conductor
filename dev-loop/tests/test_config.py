from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import EXAMPLE_JQL, load_config, load_secrets


class ConfigTests(unittest.TestCase):
    def test_given_yaml_when_load_config_then_prefixes_jql_with_project(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "config.yaml"
            p.write_text(
                "jira:\n  project: ASE\n  jql: 'assignee = currentUser()'\n",
                encoding="utf-8",
            )
            cfg = load_config(p)
            self.assertEqual(cfg.jira_project, "ASE")
            self.assertIn("project = ASE", cfg.jql)
            self.assertIn("assignee = currentUser()", cfg.jql)

    def test_given_secrets_file_when_load_then_parses_export_lines(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "secrets.env"
            p.write_text(
                "export ATLASSIAN_EMAIL='a@b.com'\nATLASSIAN_API_TOKEN=tok\n# x\n",
                encoding="utf-8",
            )
            s = load_secrets(p)
            self.assertEqual(s["ATLASSIAN_EMAIL"], "a@b.com")
            self.assertEqual(s["ATLASSIAN_API_TOKEN"], "tok")

    def test_example_jql_mentions_sprint(self) -> None:
        self.assertIn("openSprints", EXAMPLE_JQL)


    def test_given_test_profile_when_load_then_allowlist_and_no_push(self) -> None:
        root = Path(__file__).resolve().parents[1]
        cfg = load_config(root / "config.test.yaml")
        self.assertEqual(cfg.mode, "test")
        self.assertEqual(cfg.allowlist, ["devloop-lab"])
        self.assertFalse(cfg.git.push)
        self.assertFalse(cfg.git.create_pr)
        self.assertTrue(cfg.runtime.builtin_adapters)
        self.assertTrue(cfg.spec_auto_approve)
        self.assertEqual(cfg.jira.auth, "none")
        self.assertEqual(cfg.jira.project, "LAB")
        self.assertFalse(cfg.poller.enabled)
        self.assertFalse(cfg.poller.auto_merge)
        self.assertFalse(cfg.quality.snyk.enabled)
        self.assertFalse(cfg.quality.mutation.enabled)
        self.assertEqual(cfg.quality.mutation.metric, "killed")
        self.assertEqual(cfg.quality.mutation.min_pct, 75.0)
        self.assertFalse(cfg.evidence.enabled)
        self.assertFalse(cfg.workflow.enabled)
        self.assertFalse(cfg.git.stack_prs)
        self.assertEqual(cfg.autonomy.profile, "unattended")
        self.assertTrue(cfg.runtime.auto_continue)
        self.assertFalse(cfg.repo_pick.ask_when_cwd_not_repo)

    def test_given_unattended_profile_when_load_then_skips_human_spec_gate(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "config.yaml"
            p.write_text(
                "autonomy:\n  profile: unattended\n  merge: alert\n",
                encoding="utf-8",
            )
            cfg = load_config(p)
            self.assertTrue(cfg.spec_auto_approve)
            self.assertTrue(cfg.runtime.auto_continue)
            self.assertFalse(cfg.repo_pick.ask_when_cwd_not_repo)
            self.assertFalse(cfg.poller.auto_merge)
            self.assertEqual(cfg.autonomy.spec_approval, "auto")
