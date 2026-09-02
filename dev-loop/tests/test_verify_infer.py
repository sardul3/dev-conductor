from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import DevLoopConfig
from verify_infer import infer_recipe


class VerifyInferTests(unittest.TestCase):
    def test_given_gradlew_when_infer_then_uses_wrapper(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            (repo / "gradlew").write_text("#!/bin/sh\n", encoding="utf-8")
            (repo / "build.gradle").write_text("", encoding="utf-8")
            r = infer_recipe(repo, DevLoopConfig())
            self.assertIsNotNone(r)
            assert r
            self.assertEqual(r.test[0], str((repo / "gradlew").resolve()))
            self.assertIn("test", r.test)

    def test_given_no_markers_when_infer_then_none(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            (repo / "notes.txt").write_text("x", encoding="utf-8")
            self.assertIsNone(infer_recipe(repo, DevLoopConfig()))

    def test_given_override_when_infer_then_uses_config_map(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td) / "svc"
            repo.mkdir()
            cfg = DevLoopConfig(verify={"svc": {"test": "true"}}, health={"svc": "http://127.0.0.1/health"})
            r = infer_recipe(repo, cfg)
            assert r
            self.assertEqual(r.test, ["true"])
            self.assertEqual(r.health, "http://127.0.0.1/health")

    def test_given_uv_lock_when_infer_then_uv_run_pytest(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            (repo / "pyproject.toml").write_text("[project]\nname = 'demo'\n", encoding="utf-8")
            (repo / "uv.lock").write_text("# lock\n", encoding="utf-8")
            (repo / ".venv" / "bin").mkdir(parents=True)
            (repo / ".venv" / "bin" / "pytest").write_text("", encoding="utf-8")
            with patch("verify_infer.shutil.which", side_effect=lambda n: "/opt/uv" if n == "uv" else None):
                r = infer_recipe(repo, DevLoopConfig())
            assert r
            self.assertEqual(r.test, ["uv", "run", "pytest", "-q"])
            self.assertEqual(r.build, ["uv", "run", "pytest", "-q"])

    def test_given_tool_uv_and_hatch_when_infer_then_uv_run_pytest(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            (repo / "pyproject.toml").write_text(
                "[build-system]\nrequires = ['hatchling']\nbuild-backend = 'hatchling.build'\n\n"
                "[tool.uv]\ndefault-groups = ['dev']\n",
                encoding="utf-8",
            )
            with patch("verify_infer.shutil.which", side_effect=lambda n: "/opt/uv" if n == "uv" else None):
                r = infer_recipe(repo, DevLoopConfig())
            assert r
            self.assertEqual(r.test, ["uv", "run", "pytest", "-q"])

    def test_given_uv_project_when_python_tool_cmd_then_uv_run_ruff_and_pyright(self) -> None:
        from verify_infer import python_tool_cmd

        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            (repo / "uv.lock").write_text("", encoding="utf-8")
            (repo / "pyproject.toml").write_text("[tool.uv]\n", encoding="utf-8")
            with patch("verify_infer.shutil.which", side_effect=lambda n: "/opt/uv" if n == "uv" else None):
                self.assertEqual(python_tool_cmd(repo, "ruff", "check"), ["uv", "run", "ruff", "check"])
                self.assertEqual(python_tool_cmd(repo, "pyright"), ["uv", "run", "pyright"])

    def test_given_venv_pytest_without_uv_when_infer_then_venv_bin(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            (repo / "pyproject.toml").write_text("[project]\nname = 'demo'\n", encoding="utf-8")
            (repo / ".venv" / "bin").mkdir(parents=True)
            pytest_bin = repo / ".venv" / "bin" / "pytest"
            pytest_bin.write_text("", encoding="utf-8")
            with patch("verify_infer.shutil.which", return_value=None):
                r = infer_recipe(repo, DevLoopConfig())
            assert r
            self.assertEqual(r.test, [str(pytest_bin), "-q"])

    def test_given_pytest_ini_only_when_infer_then_python3_module(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            (repo / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
            with patch("verify_infer.shutil.which", return_value=None):
                r = infer_recipe(repo, DevLoopConfig())
            assert r
            self.assertEqual(r.test, ["python3", "-m", "pytest", "-q"])

    def test_given_pytest_missing_when_verify_then_log_explains_uv(self) -> None:
        from verify_infer import run_verify

        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            (repo / "pyproject.toml").write_text("[tool.uv]\n", encoding="utf-8")
            (repo / "uv.lock").write_text("", encoding="utf-8")
            log = repo / "verify.log"

            def fake_run(_repo: Path, _cmd: list[str], timeout: int | None = None) -> tuple[int, str]:
                return 1, "/usr/bin/python3: No module named pytest\n"

            with (
                patch("verify_infer.shutil.which", return_value=None),
                patch("verify_infer.run_cmd", fake_run),
            ):
                rc = run_verify(repo, DevLoopConfig(), log)
            self.assertEqual(rc, 1)
            text = log.read_text(encoding="utf-8")
            self.assertIn("no pytest in this environment; expected uv run pytest", text)
