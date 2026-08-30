#!/usr/bin/env python3
from __future__ import annotations

import shutil
import subprocess
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from config import DevLoopConfig


@dataclass
class VerifyRecipe:
    test: list[str]
    build: list[str]
    health: str | None = None


def infer_recipe(repo: Path, cfg: DevLoopConfig) -> VerifyRecipe | None:
    name = repo.resolve().name
    override = cfg.verify.get(name) or {}
    health = override.get("health") or cfg.health.get(name)
    if override.get("test"):
        test = override["test"].split()
        build = (override.get("build") or override["test"]).split()
        return VerifyRecipe(test=test, build=build, health=health)

    if (repo / "gradlew").is_file() or (repo / "build.gradle").is_file() or (repo / "build.gradle.kts").is_file():
        gw = str((repo / "gradlew").resolve()) if (repo / "gradlew").is_file() else "gradle"
        if gw == "gradle" and not shutil.which("gradle"):
            return None
        return VerifyRecipe(test=[gw, "test", "-q"], build=[gw, "test", "-q"], health=health)

    if (repo / "pom.xml").is_file():
        mvn = "./mvnw" if (repo / "mvnw").is_file() else "mvn"
        if mvn == "mvn" and not shutil.which("mvn"):
            return None
        return VerifyRecipe(test=[mvn, "-q", "test"], build=[mvn, "-q", "-DskipTests", "package"], health=health)

    if (repo / "package.json").is_file():
        if not shutil.which("npm"):
            return None
        return VerifyRecipe(test=["npm", "test", "--silent"], build=["npm", "run", "build", "--if-present"], health=health)

    if (repo / "go.mod").is_file():
        if not shutil.which("go"):
            return None
        return VerifyRecipe(test=["go", "test", "./..."], build=["go", "build", "./..."], health=health)

    if (repo / "pyproject.toml").is_file() or (repo / "pytest.ini").is_file() or (repo / "tests").is_dir():
        return VerifyRecipe(test=["python3", "-m", "pytest", "-q"], build=["python3", "-m", "pytest", "-q"], health=health)

    return None


def run_cmd(repo: Path, cmd: list[str], timeout: int | None = None) -> tuple[int, str]:
    proc = subprocess.run(cmd, cwd=str(repo), capture_output=True, text=True, timeout=timeout or 1800)
    out = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, out


def check_health(url: str, timeout: int = 8) -> tuple[bool, str]:
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            code = getattr(resp, "status", 200)
            return 200 <= int(code) < 400, f"health {code}"
    except urllib.error.HTTPError as exc:
        return 200 <= exc.code < 400, f"health {exc.code}"
    except Exception as exc:  # noqa: BLE001 — surface any health failure
        return False, str(exc)


def run_verify(repo: Path, cfg: DevLoopConfig, log_path: Path | None = None) -> int:
    recipe = infer_recipe(repo, cfg)
    if recipe is None:
        msg = (
            f"dev-loop: cannot infer test/build for {repo.name}. "
            f"Add verify.{repo.name}.test under ~/.config/dev-conductor/dev-loop/config.yaml"
        )
        if log_path:
            log_path.write_text(msg + "\n", encoding="utf-8")
        print(msg)
        return 2
    chunks: list[str] = []
    for label, cmd in (("test", recipe.test), ("build", recipe.build)):
        if cmd == recipe.build and recipe.build == recipe.test and label == "build":
            continue
        rc, out = run_cmd(repo, cmd, timeout=getattr(cfg, "verify_timeout_sec", 1800))
        chunks.append(f"$ {' '.join(cmd)}\nexit {rc}\n{out}")
        if rc != 0:
            if log_path:
                log_path.write_text("\n\n".join(chunks), encoding="utf-8")
            return rc
    if recipe.health:
        ok, msg = check_health(recipe.health)
        chunks.append(msg)
        if not ok:
            if log_path:
                log_path.write_text("\n\n".join(chunks), encoding="utf-8")
            print(msg)
            return 1
    from quality import run_quality

    qrc = run_quality(repo, cfg, chunks)
    if log_path:
        log_path.write_text("\n\n".join(chunks) or "ok\n", encoding="utf-8")
    if qrc != 0:
        return qrc
    return 0
