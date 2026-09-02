from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from agent_memory import (  # noqa: E402
    ApplyError,
    apply_from_verdict,
    apply_item,
    apply_run_memory,
)
from config import AgentMemoryCfg, DevLoopConfig  # noqa: E402


class AgentMemoryTests(unittest.TestCase):
    def test_given_agents_item_when_apply_then_appends_durable_section(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            (repo / "AGENTS.md").write_text("# Notes\n\nKeep secrets out of git.\n", encoding="utf-8")
            result = apply_item(
                repo,
                {
                    "target": "agents",
                    "text": "Isolation default is native git worktree; treehouse is opt-in.",
                    "reason": "review assumed treehouse",
                },
            )
            body = (repo / "AGENTS.md").read_text(encoding="utf-8")
            self.assertIn("## Agent memory", body)
            self.assertIn("Isolation default is native git worktree", body)
            self.assertEqual(result["path"], str(repo / "AGENTS.md"))
            self.assertEqual(result["status"], "applied")

    def test_given_duplicate_text_when_apply_then_skips(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            (repo / "AGENTS.md").write_text(
                "# Notes\n\n## Agent memory\n\n- Isolation default is native git worktree; treehouse is opt-in.\n",
                encoding="utf-8",
            )
            result = apply_item(
                repo,
                {
                    "target": "agents",
                    "text": "Isolation default is native git worktree; treehouse is opt-in.",
                },
            )
            self.assertEqual(result["status"], "skipped")
            self.assertEqual(
                (repo / "AGENTS.md").read_text(encoding="utf-8").count("Isolation default"),
                1,
            )

    def test_given_rule_item_when_apply_then_writes_path_scoped_rule(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            result = apply_item(
                repo,
                {
                    "target": "rule",
                    "path": ".claude/rules/python-tests.md",
                    "globs": ["**/*.py"],
                    "text": "Prefer pytest for new packages; do not add unittest there.",
                    "reason": "PR review",
                },
            )
            path = repo / ".claude/rules/python-tests.md"
            self.assertTrue(path.is_file())
            body = path.read_text(encoding="utf-8")
            self.assertIn("alwaysApply: false", body)
            self.assertIn("**/*.py", body)
            self.assertIn("Prefer pytest", body)
            self.assertEqual(result["status"], "applied")

    def test_given_secrets_path_when_apply_then_rejects(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            with self.assertRaises(ApplyError):
                apply_item(
                    repo,
                    {
                        "target": "rule",
                        "path": ".env",
                        "text": "leak",
                    },
                )

    def test_given_always_on_request_when_apply_then_rejects(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            with self.assertRaises(ApplyError):
                apply_item(
                    repo,
                    {
                        "target": "rule",
                        "path": ".claude/rules/global.md",
                        "globs": ["**/*"],
                        "always_apply": True,
                        "text": "never",
                    },
                )

    def test_given_verdict_metadata_when_apply_from_verdict_then_applies_all_safe(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            (repo / "AGENTS.md").write_text("# Repo\n", encoding="utf-8")
            verdict = {
                "verdict": "good-with-risks",
                "summary": "ok",
                "risks": [],
                "metadata": [
                    {
                        "target": "agents",
                        "text": "Do not use Jira MCP; REST only.",
                        "reason": "review",
                    }
                ],
            }
            applied = apply_from_verdict(repo, verdict)
            self.assertEqual(len(applied), 1)
            self.assertEqual(applied[0]["status"], "applied")
            self.assertIn("Jira MCP", (repo / "AGENTS.md").read_text(encoding="utf-8"))

    def test_given_empty_or_missing_metadata_when_apply_then_noop(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            self.assertEqual(apply_from_verdict(repo, {"verdict": "good"}), [])
            self.assertEqual(apply_from_verdict(repo, {"verdict": "good", "metadata": []}), [])

    def test_given_one_off_bug_item_when_apply_then_rejects(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            with self.assertRaises(ApplyError):
                apply_item(
                    repo,
                    {
                        "target": "agents",
                        "text": "Fix null check in FooService.",
                        "durable": False,
                    },
                )

    def test_given_verdict_and_memory_json_when_apply_run_then_writes_repo_files(self) -> None:
        cfg = DevLoopConfig(agent_memory=AgentMemoryCfg(auto_apply=True))
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td) / "repo"
            run = Path(td) / "run"
            repo.mkdir()
            run.mkdir()
            (repo / "AGENTS.md").write_text("# Repo\n", encoding="utf-8")
            (run / "verdict.json").write_text(
                json.dumps(
                    {
                        "verdict": "good",
                        "metadata": [
                            {
                                "target": "agents",
                                "text": "Do not use Jira MCP; REST only.",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            (run / "memory.json").write_text(
                json.dumps(
                    {
                        "metadata": [
                            {
                                "target": "rule",
                                "path": ".claude/rules/python-http.mdc",
                                "globs": ["**/*.py"],
                                "text": "Health handlers must not catch-all Exception into HTTP 200.",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            results = apply_run_memory(cfg, repo, run)
            statuses = {r["status"] for r in results}
            self.assertEqual(statuses, {"applied"})
            self.assertIn("Jira MCP", (repo / "AGENTS.md").read_text(encoding="utf-8"))
            rule = repo / ".claude/rules/python-http.mdc"
            self.assertTrue(rule.is_file())
            self.assertIn("alwaysApply: false", rule.read_text(encoding="utf-8"))
            applied = json.loads((run / "memory-applied.json").read_text(encoding="utf-8"))
            self.assertEqual(len(applied), 2)

    def test_given_auto_apply_off_when_apply_run_then_noop(self) -> None:
        cfg = DevLoopConfig(agent_memory=AgentMemoryCfg(auto_apply=False))
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td) / "repo"
            run = Path(td) / "run"
            repo.mkdir()
            run.mkdir()
            (run / "verdict.json").write_text(
                json.dumps({"metadata": [{"target": "agents", "text": "x"}]}),
                encoding="utf-8",
            )
            self.assertEqual(apply_run_memory(cfg, repo, run), [])
            self.assertFalse((run / "memory-applied.json").is_file())


if __name__ == "__main__":
    unittest.main()
