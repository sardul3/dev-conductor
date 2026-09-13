from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from unittest.mock import patch
from ship import branch_name, conventional_message, create_pr, pr_body, slugify


class ShipTests(unittest.TestCase):
    def test_given_summary_when_branch_name_then_feat_key_slug(self) -> None:
        self.assertEqual(branch_name("ASE-12", "Add Health Check!"), "feat/ASE-12-add-health-check")

    def test_given_summary_when_conventional_message_then_type_and_key(self) -> None:
        msg = conventional_message("ASE-12", "Add health check", "Do actuator.")
        self.assertTrue(msg.startswith("feat: Add health check (ASE-12)"))
        self.assertIn("Do actuator.", msg)

    def test_slugify_strips_noise(self) -> None:
        self.assertEqual(slugify("Hello, World!!"), "hello-world")

    def test_given_base_when_create_pr_then_passes_flag(self) -> None:
        with patch("ship.subprocess.run") as run:
            run.return_value.returncode = 0
            run.return_value.stdout = "https://github.com/org/repo/pull/12\n"
            run.return_value.stderr = ""
            n = create_pr(Path("/tmp"), "feat: x (A-1)", "body", base="feat/A-1")
            self.assertEqual(n, 12)
            cmd = run.call_args[0][0]
            self.assertIn("--base", cmd)
            self.assertIn("feat/A-1", cmd)

    def test_given_only_untracked_when_commit_then_skips(self) -> None:
        import subprocess
        import tempfile
        from ship import commit_if_needed
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            subprocess.check_call(["git", "init", "-q"], cwd=td)
            subprocess.check_call(["git", "config", "user.email", "t@t"], cwd=td)
            subprocess.check_call(["git", "config", "user.name", "t"], cwd=td)
            (repo / "keep.txt").write_text("a\n", encoding="utf-8")
            subprocess.check_call(["git", "add", "keep.txt"], cwd=td)
            subprocess.check_call(["git", "commit", "-qm", "init"], cwd=td)
            (repo / "noise.txt").write_text("x\n", encoding="utf-8")
            self.assertFalse(commit_if_needed(repo, "feat: no (A-1)\n"))

    def test_given_ticket_when_pr_body_then_jira_link_recipe_no_spec(self) -> None:
        spec = (
            "## Spec\nGiven a clean checkout\nWhen tests run\nThen they pass\n"
        )
        body = pr_body(
            "LCN-2",
            "Initialize Python project",
            spec,
            {"verdict": "good", "summary": "scaffolding ok", "risks": []},
            True,
            jira_base="https://ex.atlassian.net",
            test_commands=["uv run pytest -q", "uv run ruff check ."],
            verify_log="$ uv run pytest -q\nexit 0\n1 passed\n",
        )
        self.assertIn("https://ex.atlassian.net/browse/LCN-2", body)
        self.assertIn("[LCN-2](https://ex.atlassian.net/browse/LCN-2)", body)
        self.assertNotIn("Jira: LCN-2\n", body)
        self.assertNotIn("## Spec", body)
        self.assertNotIn("Given a clean checkout", body)
        self.assertIn("uv run pytest -q", body)
        self.assertIn("uv run ruff check .", body)
        self.assertNotIn("run the project test command", body)
        self.assertIn("## Evidence", body)
        self.assertIn("exit 0", body)

    def test_given_visual_files_when_pr_body_then_image_markdown(self) -> None:
        body = pr_body(
            "LCN-2",
            "Initialize Python project",
            "## Spec\nGiven a clean checkout\n",
            {"verdict": "good", "summary": "ok"},
            True,
            jira_base="https://ex.atlassian.net",
            test_commands=["uv run pytest -q"],
            visual=True,
            visual_files=["tests.png", "run.png"],
        )
        self.assertIn("## Evidence", body)
        self.assertIn("![tests](tests.png)", body)
        self.assertIn("![run](run.png)", body)
        self.assertNotIn("## Spec", body)
        self.assertIn("https://ex.atlassian.net/browse/LCN-2", body)

    def test_given_require_visual_and_no_files_when_ship_then_refuses(self) -> None:
        from config import DevLoopConfig
        from evidence import VisualEvidenceMissing
        from ship import ship_work

        cfg = DevLoopConfig()
        cfg.evidence.require_visual = True
        cfg.git.push = True
        cfg.git.create_pr = True
        with tempfile.TemporaryDirectory() as td:
            run = Path(td) / "run"
            run.mkdir()
            repo = Path(td) / "repo"
            with patch("ship.create_pr") as create:
                with self.assertRaises(VisualEvidenceMissing) as ctx:
                    ship_work(repo, [], "LCN-2", "init", "", None, cfg, run=run)
                create.assert_not_called()
                msg = str(ctx.exception)
                self.assertIn("evidence", msg.lower())
                self.assertIn(str(run / "evidence"), msg)

    def test_given_visual_when_pr_body_then_requires_screenshots(self) -> None:
        body = pr_body(
            "ASE-9",
            "Add dashboard",
            "full spec dump",
            {"verdict": "good", "summary": "ok"},
            True,
            jira_base="https://acme.atlassian.net",
            test_commands=["npm test"],
            visual=True,
        )
        self.assertIn("https://acme.atlassian.net/browse/ASE-9", body)
        self.assertNotIn("## Spec", body)
        self.assertRegex(body, r"(?i)screenshot|video")

    def test_given_uv_pyproject_when_pr_test_commands_then_recipe_tools(self) -> None:
        import tempfile
        from config import DevLoopConfig
        from ship import pr_test_commands

        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            (repo / "uv.lock").write_text("# lock\n", encoding="utf-8")
            (repo / "pyproject.toml").write_text(
                "[project]\nname = 'demo'\n\n[tool.uv]\n\n[tool.ruff]\n\n[tool.pyright]\n",
                encoding="utf-8",
            )
            src = repo / "src" / "demo_pkg"
            src.mkdir(parents=True)
            (src / "__main__.py").write_text("print('hi')\n", encoding="utf-8")
            with patch("verify_infer.shutil.which", side_effect=lambda n: "/opt/uv" if n == "uv" else None):
                cmds = pr_test_commands(repo, DevLoopConfig())
            joined = "\n".join(cmds)
            self.assertIn("uv sync", joined)
            self.assertIn("uv run pytest", joined)
            self.assertIn("uv run ruff check .", joined)
            self.assertIn("uv run pyright", joined)
            self.assertIn("uv run python -m demo_pkg", joined)
