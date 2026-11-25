from __future__ import annotations

import json
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from verify_pipeline import (  # noqa: E402
    VerifyInput,
    api_doc_problem,
    banned_comment_hits,
    antipattern_hits,
    classify_cves,
    fixer_violation,
    human_name,
    introduced_packages,
    parse_diff_coverage,
    plan_gates,
    resolve_risk,
    run_pipeline,
    sensitive_spec_gaps,
    should_diagrams,
    smell_actions,
)


def _inp(**kwargs) -> VerifyInput:
    base = dict(
        risk_class="normal",
        changed=("src/pay/pay.py",),
        changed_lines=80,
        commands={
            "unit": "unit",
            "coverage": "coverage",
            "pit": "pit",
            "security": "security",
        },
    )
    base.update(kwargs)
    cmds = dict(base.get("commands") or {})
    base["commands"] = cmds
    return VerifyInput(**base)


class PlanTests(unittest.TestCase):
    def test_given_safe_when_plan_then_static_unit_and_coverage_only(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            (repo / "src/pay").mkdir(parents=True)
            (repo / "src/pay/pay.py").write_text("x = 1\n", encoding="utf-8")
            names = {(c.name, c.stage) for c in plan_gates(repo, _inp(risk_class="safe"))}
        self.assertIn(("banned_comments", "A"), names)
        self.assertIn(("api_doc", "A"), names)
        self.assertIn(("antipattern", "A"), names)
        self.assertIn(("unit", "B"), names)
        self.assertIn(("coverage", "B"), names)
        stages = {stage for _, stage in names}
        self.assertNotIn("C", stages)
        self.assertNotIn(("pit", "B"), names)
        self.assertNotIn(("security", "D"), names)
        self.assertNotIn(("browser", "C"), names)
        self.assertNotIn(("docker_health", "C"), names)
        for banned in ("deploy", "canary", "soak", "shadow", "chaos", "release"):
            self.assertNotIn(banned, {n for n, _ in names})

    def test_given_normal_and_boot_when_plan_then_includes_smoke_with_health_not_in_b(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            (repo / "src/pay").mkdir(parents=True)
            (repo / "src/pay/pay.py").write_text("x = 1\n", encoding="utf-8")
            checks = plan_gates(repo, _inp(commands={
                "unit": "unit",
                "coverage": "coverage",
                "pit": "pit",
                "security": "security",
                "health": "http://127.0.0.1:9/health",
                "smoke": "smoke",
            }))
        by = {c.name: c for c in checks}
        self.assertEqual(by["smoke"].stage, "C")
        self.assertNotEqual(by["contract"].stage, "B") if "contract" in by else None
        self.assertEqual(by["pit"].stage, "B")
        self.assertEqual(by["security"].stage, "D")
        self.assertNotIn("browser", by)

    def test_given_contract_command_when_plan_then_stage_a(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            checks = plan_gates(repo, _inp(risk_class="safe", commands={
                "unit": "unit", "coverage": "coverage", "contract": "contract-tests",
            }))
        contract = next(c for c in checks if c.name == "contract")
        self.assertEqual(contract.stage, "A")
        self.assertTrue(contract.required)

    def test_given_property_on_changed_module_when_normal_then_planned(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            (repo / "src/pay").mkdir(parents=True)
            (repo / "src/pay/pay.py").write_text("x = 1\n", encoding="utf-8")
            (repo / "src/pay/property_pay.py").write_text("def test_prop():\n    pass\n", encoding="utf-8")
            (repo / "src/other").mkdir()
            (repo / "src/other/property_other.py").write_text("x\n", encoding="utf-8")
            checks = plan_gates(repo, _inp())
        prop = next(c for c in checks if c.name == "property")
        self.assertIn("property_pay.py", prop.command)
        self.assertNotIn("property_other.py", prop.command)
        self.assertNotIn("fuzz", {c.name for c in checks})

    def test_given_sensitive_without_property_files_when_plan_then_property_and_fuzz_required(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            (repo / "src").mkdir()
            (repo / "src/pay.py").write_text("x = 1\n", encoding="utf-8")
            spec = "## Threat model\nstride\n\n## Pen test\nnotes\n"
            checks = plan_gates(repo, _inp(risk_class="sensitive", spec=spec, changed=("src/pay.py",)))
        by = {c.name: c for c in checks}
        self.assertTrue(by["property"].required)
        self.assertTrue(by["fuzz"].required)
        self.assertEqual(by["threat_model"].stage, "A")
        self.assertEqual(by["pen_test_input"].kind, "spec")
        self.assertNotIn("pentest", by)
        self.assertFalse(by["smells"].autofix)

    def test_given_hot_path_when_plan_then_benchmark_else_not(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            hot = plan_gates(repo, _inp(changed=("svc/hot/cache.py",), commands={
                "unit": "unit", "coverage": "coverage", "pit": "pit", "security": "security",
                "benchmark": "bench",
            }))
            cold = plan_gates(repo, _inp(changed=("svc/cache.py",)))
        self.assertIn("benchmark", {c.name for c in hot})
        self.assertNotIn("benchmark", {c.name for c in cold})

    def test_given_auth_path_when_resolve_then_sensitive_unless_ticket_overrides(self) -> None:
        escalated = resolve_risk(_inp(risk_class="safe", changed=("src/auth/login.py",)))
        pinned = resolve_risk(_inp(risk_class="safe", explicit_risk="safe", changed=("src/auth/login.py",)))
        self.assertEqual(escalated, "sensitive")
        self.assertEqual(pinned, "safe")

    def test_given_no_boot_when_normal_then_stage_c_omitted(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            checks = plan_gates(repo, _inp())
        self.assertNotIn("C", {c.stage for c in checks})


class BuiltinCheckTests(unittest.TestCase):
    def test_given_todo_without_exemption_when_scan_then_hit(self) -> None:
        self.assertTrue(banned_comment_hits("x = 1  # TODO later\n"))
        self.assertFalse(banned_comment_hits("x = 1  # TODO lint:allow-comment: protocol quirk\n"))

    def test_given_swallowed_exception_when_scan_then_hit(self) -> None:
        self.assertTrue(antipattern_hits("try:\n    a()\nexcept Exception:\n    pass\n"))
        self.assertFalse(antipattern_hits("try:\n    a()\nexcept Exception:\n    raise\n"))

    def test_given_handler_change_without_spec_when_api_doc_then_drift(self) -> None:
        msg = api_doc_problem(
            ["src/PayController.java"],
            ["src/PayController.java", "openapi.yaml"],
        )
        self.assertIn("openapi.yaml", msg)
        self.assertEqual(api_doc_problem(["src/pay.py"], ["src/pay.py"]), "")

    def test_given_new_dep_cve_when_classify_then_fails_and_baseline_is_recorded(self) -> None:
        findings = [
            {"id": "CVE-1", "package": "old-lib", "in_diff": False},
            {"id": "CVE-2", "package": "old-lib", "in_diff": True},
            {"id": "CVE-1", "package": "left-pad", "in_diff": False},
        ]
        failing, recorded = classify_cves(findings, {"CVE-1"}, {"left-pad"})
        self.assertEqual({f["id"] for f in failing}, {"CVE-2", "CVE-1"})
        self.assertEqual(recorded[0]["id"], "CVE-1")
        self.assertEqual(recorded[0]["package"], "old-lib")

    def test_given_requirements_diff_when_parse_then_introduced_name(self) -> None:
        diff = "--- a/requirements.txt\n+++ b/requirements.txt\n+left-pad==1.0\n"
        self.assertEqual(introduced_packages(diff), {"left-pad"})

    def test_given_sensitive_spec_when_gaps_then_names_missing_inputs(self) -> None:
        self.assertEqual(
            sensitive_spec_gaps("## Behavior\nok\n"),
            ["threat model", "pen test"],
        )
        self.assertEqual(
            sensitive_spec_gaps("## Threat model\nstride\n\n## Penetration test\nscoped\n"),
            [],
        )

    def test_given_human_file_when_name_then_rejects_blank_and_auto(self) -> None:
        self.assertEqual(human_name("  Ada Lovelace\n"), "Ada Lovelace")
        self.assertIsNone(human_name("auto"))
        self.assertIsNone(human_name("  "))

    def test_given_coverage_line_when_parse_then_pct(self) -> None:
        self.assertEqual(parse_diff_coverage("diff coverage: 81%\n"), 81.0)
        self.assertIsNone(parse_diff_coverage("TOTAL 90%\n"))

    def test_given_safe_or_tiny_when_diagrams_then_skip(self) -> None:
        self.assertFalse(should_diagrams("safe", 200, 40))
        self.assertFalse(should_diagrams("normal", 10, 40))
        self.assertTrue(should_diagrams("normal", 80, 40))


class FixerTests(unittest.TestCase):
    def test_given_defining_test_edit_when_guard_then_refuses(self) -> None:
        msg = fixer_violation(
            {"tests/test_pay.py": "aaa"},
            {"tests/test_pay.py": "bbb"},
            {"tests/test_pay.py", "src/pay.py"},
            {"tests/test_pay.py"},
            {"pit": 75.0},
            {"pit": 75.0},
        )
        self.assertIn("defining test", msg)

    def test_given_file_outside_ticket_when_guard_then_refuses(self) -> None:
        msg = fixer_violation(
            {"tests/test_pay.py": "aaa"},
            {"tests/test_pay.py": "aaa"},
            {"src/pay.py"},
            {"other/unrelated.py"},
            {"pit": 75.0},
            {"pit": 75.0},
        )
        self.assertIn("expanded past ticket", msg)

    def test_given_lower_floor_when_guard_then_refuses(self) -> None:
        msg = fixer_violation(
            {},
            {},
            {"src/pay.py"},
            {"src/pay.py"},
            {"pit": 75.0, "coverage": 80.0},
            {"pit": 70.0, "coverage": 80.0},
        )
        self.assertIn("threshold", msg)

    def test_given_same_module_file_when_guard_then_allows(self) -> None:
        msg = fixer_violation(
            {"tests/test_pay.py": "aaa"},
            {"tests/test_pay.py": "aaa"},
            {"src/pay.py"},
            {"src/extra.py"},
            {"pit": 75.0},
            {"pit": 80.0},
        )
        self.assertEqual(msg, "")

    def test_given_smells_when_actions_then_fix_in_diff_only_and_sensitive_never(self) -> None:
        findings = [
            {"path": "src/pay.py", "kind": "trailing_ws"},
            {"path": "src/other.py", "kind": "trailing_ws"},
            {"path": "tests/test_pay.py", "kind": "trailing_ws"},
        ]
        fixes, intents = smell_actions(findings, {"src/pay.py", "tests/test_pay.py"}, "normal", cap=2)
        self.assertEqual([f["path"] for f in fixes], ["src/pay.py"])
        self.assertEqual(intents[0]["path"], "src/other.py")
        none, _ = smell_actions(findings, {"src/pay.py"}, "sensitive", cap=2)
        self.assertEqual(none, [])

    def test_given_cap_when_many_smells_then_stops(self) -> None:
        findings = [{"path": f"src/{i}.py", "kind": "trailing_ws"} for i in range(3)]
        touched = {f"src/{i}.py" for i in range(3)}
        fixes, _ = smell_actions(findings, touched, "normal", cap=2)
        self.assertEqual(len(fixes), 2)


class PipelineTests(unittest.TestCase):
    def _runner(self, script: dict[str, tuple[int, str]]):
        calls: list[str] = []

        def runner(_repo: Path, cmd: list[str], timeout: int | None = None) -> tuple[int, str]:
            line = " ".join(cmd)
            calls.append(line)
            if line not in script:
                return 1, f"unexpected {line}"
            return script[line]

        runner.calls = calls  # type: ignore[attr-defined]
        return runner

    def test_given_lint_fails_when_run_then_other_static_runs_and_unit_does_not(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            (repo / "src").mkdir()
            (repo / "src/pay.py").write_text("x = 1\n", encoding="utf-8")
            dest = Path(td) / "run"
            runner = self._runner({
                "lint": (1, "lint bad"),
                "arch": (0, "arch ok"),
                "unit": (0, "ok"),
                "coverage": (0, "diff coverage: 100%\n"),
            })
            result = run_pipeline(
                repo,
                _inp(risk_class="safe", changed=("src/pay.py",), commands={
                    "lint": "lint",
                    "architecture": "arch",
                    "unit": "unit",
                    "coverage": "coverage",
                }),
                dest,
                runner=runner,
            )
        self.assertEqual(result.exit_code, 1)
        self.assertFalse(result.pr_allowed)
        self.assertIn("lint", runner.calls)
        self.assertIn("arch", runner.calls)
        self.assertNotIn("unit", runner.calls)

    def test_given_component_red_when_run_then_stops_before_later_suites(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            (repo / "src").mkdir()
            (repo / "src/pay.py").write_text("x = 1\n", encoding="utf-8")
            runner = self._runner({
                "unit": (0, "ok"),
                "component": (1, "red"),
                "regression": (0, "ok"),
                "coverage": (0, "diff coverage: 100%\n"),
            })
            result = run_pipeline(
                repo,
                _inp(risk_class="safe", changed=("src/pay.py",), commands={
                    "unit": "unit",
                    "component": "component",
                    "regression": "regression",
                    "coverage": "coverage",
                }),
                Path(td) / "run",
                runner=runner,
            )
        self.assertEqual(result.exit_code, 1)
        self.assertIn("component", runner.calls)
        self.assertNotIn("regression", runner.calls)
        self.assertNotIn("coverage", runner.calls)

    def test_given_pit_below_floor_when_normal_then_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            (repo / "src").mkdir()
            (repo / "src/pay.py").write_text("x = 1\n", encoding="utf-8")
            runner = self._runner({
                "unit": (0, "ok"),
                "coverage": (0, "diff coverage: 90%\n"),
                "pit": (0, "Killed 10 (74%)\n"),
                "security": (0, '{"ok": true, "vulnerabilities": []}\n'),
            })
            result = run_pipeline(repo, _inp(changed=("src/pay.py",)), Path(td) / "run", runner=runner)
        self.assertEqual(result.exit_code, 1)
        pit = next(c for c in result.checks if c.name == "pit")
        self.assertEqual(pit.status, "fail")

    def test_given_green_normal_when_run_then_bundle_and_pr(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            (repo / "src").mkdir()
            (repo / "web").mkdir()
            (repo / "src/pay.py").write_text("x = 1\n", encoding="utf-8")
            (repo / "web/app.tsx").write_text("export const A = 1\n", encoding="utf-8")
            runner = self._runner({
                "unit": (0, "ok"),
                "coverage": (0, "diff coverage: 90%\n"),
                "pit": (0, "Killed 10 (80%)\n"),
                "security": (0, '{"ok": true, "vulnerabilities": [{"id": "CVE-1", "packageName": "old-lib"}]}\n'),
                "browser": (0, "shot ok"),
            })
            (repo / ".devloop").mkdir()
            (repo / ".devloop/cve-baseline.json").write_text('{"ids": ["CVE-1"]}\n', encoding="utf-8")
            dest = Path(td) / "run"
            result = run_pipeline(
                repo,
                _inp(
                    changed=("src/pay.py", "web/app.tsx"),
                    changed_lines=120,
                    commands={
                        "unit": "unit",
                        "coverage": "coverage",
                        "pit": "pit",
                        "security": "security",
                        "browser": "browser",
                    },
                ),
                dest,
                runner=runner,
            )
            self.assertEqual(result.exit_code, 0, result.reason)
            self.assertTrue(result.pr_allowed)
            self.assertTrue((dest / "verify-bundle" / "manifest.json").is_file())
            self.assertTrue((dest / "verify-bundle" / "diagrams" / "feature-map.md").is_file())
            self.assertTrue((dest / "verify-bundle" / "diagrams" / "architecture.md").is_file())
            manifest = json.loads((dest / "verify-bundle" / "manifest.json").read_text(encoding="utf-8"))
            self.assertTrue(manifest["pr_allowed"])
            security = (dest / "verify-bundle" / "security.json").read_text(encoding="utf-8")
            self.assertIn("CVE-1", security)

    def test_given_safe_tiny_when_run_then_logs_without_diagrams(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            (repo / "src").mkdir()
            (repo / "src/pay.py").write_text("x = 1\n", encoding="utf-8")
            runner = self._runner({
                "unit": (0, "ok"),
                "coverage": (0, "diff coverage: 100%\n"),
            })
            dest = Path(td) / "run"
            result = run_pipeline(
                repo,
                _inp(risk_class="safe", changed=("src/pay.py",), changed_lines=8, commands={
                    "unit": "unit", "coverage": "coverage",
                }),
                dest,
                runner=runner,
            )
            self.assertTrue(result.pr_allowed)
            self.assertTrue((dest / "verify-bundle" / "logs" / "unit.log").is_file())
            self.assertFalse((dest / "verify-bundle" / "diagrams").exists())

    def test_given_sensitive_without_human_when_green_then_stops(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            (repo / "src").mkdir()
            (repo / "src/pay.py").write_text("x = 1\n", encoding="utf-8")
            (repo / "src/property_pay.py").write_text("def test_p():\n    assert True\n", encoding="utf-8")
            (repo / "src/fuzz_pay.py").write_text("def test_f():\n    assert True\n", encoding="utf-8")
            script = {
                "unit": (0, "ok"),
                "coverage": (0, "diff coverage: 90%\n"),
                "pit": (0, "Killed 3 (80%)\n"),
                "security": (0, '{"ok": true, "vulnerabilities": []}\n'),
            }

            def runner(_repo: Path, cmd: list[str], timeout: int | None = None) -> tuple[int, str]:
                line = " ".join(cmd)
                if line in script:
                    return script[line]
                if "property" in line or "fuzz" in line:
                    return 0, "ok"
                return 1, f"unexpected {line}"

            spec = "## Threat model\nstride\n\n## Pen test\nnotes\n"
            dest = Path(td) / "run"
            blocked = run_pipeline(
                repo,
                _inp(risk_class="sensitive", spec=spec, changed=("src/pay.py",), changed_lines=20),
                dest,
                runner=runner,
            )
            allowed = run_pipeline(
                repo,
                _inp(
                    risk_class="sensitive",
                    spec=spec,
                    human_text="Grace Hopper",
                    changed=("src/pay.py",),
                    changed_lines=20,
                ),
                Path(td) / "run2",
                runner=runner,
            )
        self.assertTrue(blocked.waiting_human)
        self.assertFalse(blocked.pr_allowed)
        self.assertEqual(blocked.exit_code, 3)
        self.assertTrue(allowed.pr_allowed, allowed.reason)
        self.assertIn("Grace Hopper", allowed.reason)

    def test_given_boot_when_normal_then_smoke_records_health(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            (repo / "src").mkdir()
            (repo / "src/pay.py").write_text("x = 1\n", encoding="utf-8")
            runner = self._runner({
                "unit": (0, "ok"),
                "coverage": (0, "diff coverage: 90%\n"),
                "pit": (0, "Killed 3 (80%)\n"),
                "security": (0, '{"ok": true, "vulnerabilities": []}\n'),
                "boot": (0, "started"),
            })

            def health(_url: str, timeout: int = 8) -> tuple[bool, str]:
                return True, "health 200"

            dest = Path(td) / "run"
            result = run_pipeline(
                repo,
                _inp(commands={
                    "unit": "unit",
                    "coverage": "coverage",
                    "pit": "pit",
                    "security": "security",
                    "nondocher": "boot",
                    "health": "http://127.0.0.1:9/health",
                }),
                dest,
                runner=runner,
                health=health,
            )
            self.assertEqual(result.exit_code, 0, result.reason)
            smoke = next(c for c in result.checks if c.name == "smoke")
            self.assertEqual(smoke.stage, "C")
            self.assertEqual(smoke.status, "pass")
            self.assertIn("health 200", (dest / "verify-bundle" / "health.txt").read_text(encoding="utf-8"))

    def test_given_trailing_ws_when_fix_keeps_gates_then_only_ticket_file_changes(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            (repo / "src").mkdir()
            (repo / "src/pay.py").write_text("x = 1   \n", encoding="utf-8")
            (repo / "src/other.py").write_text("y = 2   \n", encoding="utf-8")
            runner = self._runner({
                "unit": (0, "ok"),
                "coverage": (0, "diff coverage: 100%\n"),
            })
            run_pipeline(
                repo,
                _inp(risk_class="safe", changed=("src/pay.py",), changed_lines=4, commands={
                    "unit": "unit", "coverage": "coverage",
                }),
                Path(td) / "run",
                runner=runner,
            )
            self.assertEqual((repo / "src/pay.py").read_text(encoding="utf-8"), "x = 1\n")
            self.assertTrue((repo / "src/other.py").read_text(encoding="utf-8").endswith("   \n"))

    def test_given_missing_unit_command_when_run_then_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            result = run_pipeline(
                repo,
                VerifyInput(risk_class="safe", changed=("src/a.py",), commands={"coverage": "coverage"}),
                Path(td) / "run",
                runner=self._runner({}),
            )
        self.assertEqual(result.exit_code, 1)
        self.assertFalse(result.pr_allowed)
        unit = next(c for c in result.checks if c.name == "unit")
        self.assertEqual(unit.status, "fail")


class ConfigWireTests(unittest.TestCase):
    def test_given_test_profile_when_load_then_safe_verification(self) -> None:
        from config import load_config

        cfg = load_config(Path(__file__).resolve().parents[1] / "config.test.yaml")
        self.assertTrue(cfg.verification.enabled)
        self.assertEqual(cfg.verification.risk_class, "safe")
        self.assertEqual(cfg.verification.pit_min_pct, 75.0)
        self.assertIn("diff coverage", cfg.verification.commands.get("coverage", ""))

    def test_given_no_verification_key_when_load_then_normal_defaults(self) -> None:
        from config import load_config

        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "config.yaml"
            p.write_text("mode: prod\n", encoding="utf-8")
            cfg = load_config(p)
        self.assertTrue(cfg.verification.enabled)
        self.assertEqual(cfg.verification.risk_class, "normal")
        self.assertEqual(cfg.verification.fix_cap, 2)
        self.assertEqual(cfg.verification.pit_min_pct, 75.0)
