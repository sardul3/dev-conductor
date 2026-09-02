from __future__ import annotations

import json
import secrets
import shutil
import subprocess
import threading
import time
import webbrowser
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .builder import BuildBlocked, build_bundle
from .drawio import load_icons
from .model import all_findings, atomic_write, finding_summary, load_model, pretty_json_bytes, validate_structure


MAX_BODY = 2 * 1024 * 1024
MAX_MESSAGE = 4000


class ClaudeBridge:
    def __init__(
        self,
        *,
        enabled: bool,
        model_path: Path,
        output_directory: Path,
        skill_root: Path,
        generator_version: str,
        session: str | None,
        timeout: int,
        max_budget_usd: float,
    ) -> None:
        self.enabled = enabled
        self.model_path = model_path
        self.output_directory = output_directory
        self.skill_root = skill_root
        self.generator_version = generator_version
        self.session = session
        self.timeout = timeout
        self.max_budget_usd = max_budget_usd
        self.lock = threading.Lock()
        self.icons = load_icons(skill_root / "assets" / "azure-icons.json")

    def chat(self, message: str, review: dict[str, Any] | None) -> dict[str, Any]:
        if not self.enabled:
            raise PermissionError("Claude bridge is disabled. Restart serve with --claude-bridge or use Copy change prompt.")
        if not message or len(message) > MAX_MESSAGE:
            raise ValueError(f"Message must contain 1 to {MAX_MESSAGE} characters.")
        if not shutil.which("claude"):
            raise RuntimeError("The claude CLI is not available on PATH.")
        with self.lock:
            model = load_model(self.model_path)
            prompt = self._prompt(model, message, review or {})
            schema = {
                "type": "object",
                "additionalProperties": False,
                "required": ["reply", "changed", "candidate_model"],
                "properties": {
                    "reply": {"type": "string"},
                    "changed": {"type": "boolean"},
                    "candidate_model": {"type": "object"},
                },
            }
            command = [
                "claude",
                "-p",
                "--output-format",
                "json",
                "--tools",
                "",
                "--max-turns",
                "1",
                "--max-budget-usd",
                str(self.max_budget_usd),
                "--json-schema",
                json.dumps(schema, separators=(",", ":")),
            ]
            if self.session:
                command.extend(["--resume", self.session])
            command.append(prompt)
            completed = subprocess.run(
                command,
                cwd=self.model_path.parent,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                check=False,
            )
            if completed.returncode != 0:
                error = completed.stderr.strip() or completed.stdout.strip() or f"claude exited {completed.returncode}"
                raise RuntimeError(error[-2000:])
            raw = json.loads(completed.stdout)
            if raw.get("session_id"):
                self.session = str(raw["session_id"])
            response = raw.get("structured_output")
            if not isinstance(response, dict):
                response = raw.get("result")
                if isinstance(response, str):
                    response = json.loads(response)
            if not isinstance(response, dict):
                raise RuntimeError("Claude returned no structured architecture response.")
            reply = str(response.get("reply", ""))
            if not response.get("changed"):
                return {"reply": reply, "applied": False, "session_id": self.session}
            candidate = response.get("candidate_model")
            if not isinstance(candidate, dict):
                raise ValueError("Claude marked the model changed but returned no candidate_model object.")
            structural = validate_structure(candidate, set(self.icons))
            blockers = [item for item in structural if item.blocking]
            if blockers:
                return {"reply": reply or "The proposed revision was not applied.", "applied": False, "session_id": self.session, "validation": [item.to_dict() for item in blockers[:40]]}
            backup_dir = self.output_directory / "backups"
            backup_dir.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            backup = backup_dir / f"{model.get('project', {}).get('id', 'architecture')}-{stamp}.arch.json"
            atomic_write(backup, pretty_json_bytes(model))
            atomic_write(self.model_path, pretty_json_bytes(candidate))
            try:
                result = build_bundle(candidate, self.output_directory, self.skill_root, strict=False, generator_version=self.generator_version)
            except Exception:
                atomic_write(self.model_path, pretty_json_bytes(model))
                raise
            return {"reply": reply, "applied": True, "session_id": self.session, "gate": result.summary, "backup": backup.name}

    def _prompt(self, model: dict[str, Any], message: str, review: dict[str, Any]) -> str:
        change_items = [
            {"object": key, "status": value.get("status"), "comment": value.get("comment", "")}
            for key, value in (review.get("objects", {}) if isinstance(review, dict) else {}).items()
            if isinstance(value, dict) and value.get("status") in {"modify", "rejected"}
        ]
        return (
            "You are the constrained architecture revision engine for Arch Studio. "
            "Return only the requested structured response. You have no tools. "
            "The canonical model below is authoritative. Apply the reviewer's request only when it changes the visual specification. "
            "Preserve unrelated architecture and UI stable IDs, content, contracts, and placements. Update affected decisions, risks, assumptions, requirements, controls, UI states, bindings, acceptance coverage, and traceability. "
            "Do not remove or falsify governance data to force a pass. Do not invent tenant facts, SLOs, owners, IP ranges, costs, compliance, or runtime evidence. "
            "If clarification is necessary, set changed=false, return the current model unchanged as candidate_model, and ask one focused question in reply. "
            "When changed=true, return the complete revised model in candidate_model.\n\n"
            f"Reviewer message:\n{message}\n\n"
            f"Outstanding review changes:\n{json.dumps(change_items, ensure_ascii=False)}\n\n"
            f"Canonical model:\n{json.dumps(model, ensure_ascii=False)}"
        )


class ReviewServer:
    def __init__(
        self,
        *,
        model_path: Path,
        output_directory: Path,
        skill_root: Path,
        generator_version: str,
        port: int,
        claude_bridge: bool,
        claude_session: str | None,
        timeout: int,
        max_budget_usd: float,
    ) -> None:
        self.model_path = model_path.resolve()
        self.output_directory = output_directory.resolve()
        self.skill_root = skill_root.resolve()
        self.generator_version = generator_version
        self.port = port
        self.token = secrets.token_urlsafe(32)
        self.bridge = ClaudeBridge(
            enabled=claude_bridge,
            model_path=self.model_path,
            output_directory=self.output_directory,
            skill_root=self.skill_root,
            generator_version=generator_version,
            session=claude_session,
            timeout=timeout,
            max_budget_usd=max_budget_usd,
        )
        self.httpd: ThreadingHTTPServer | None = None

    def start(self, *, open_browser: bool) -> None:
        model = load_model(self.model_path)
        build_bundle(model, self.output_directory, self.skill_root, strict=False, generator_version=self.generator_version)
        state = self

        class Handler(BaseHTTPRequestHandler):
            server_version = "ArchStudio/1.0"

            def log_message(self, fmt: str, *args: Any) -> None:
                return

            def do_GET(self) -> None:
                path = urlparse(self.path).path
                if path == "/api/health":
                    if not self._authorized():
                        return
                    self._json(HTTPStatus.OK, {"status": "ok", "claude_bridge": state.bridge.enabled, "session_attached": bool(state.bridge.session)})
                    return
                if path in {"/", "/review.html"}:
                    content = (state.output_directory / "review.html").read_bytes().replace(b"__ARCH_STUDIO_CSRF__", state.token.encode("ascii"))
                    self._bytes(HTTPStatus.OK, content, "text/html; charset=utf-8")
                    return
                allowed = {item.name for item in state.output_directory.iterdir() if item.is_file() and item.suffix in {".drawio", ".json", ".md", ".csv"}}
                name = path.lstrip("/")
                if name not in allowed:
                    self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})
                    return
                content_type = "application/json" if name.endswith(".json") else "text/markdown; charset=utf-8" if name.endswith(".md") else "text/csv; charset=utf-8" if name.endswith(".csv") else "application/xml; charset=utf-8"
                self._bytes(HTTPStatus.OK, (state.output_directory / name).read_bytes(), content_type)

            def do_POST(self) -> None:
                if not self._authorized():
                    return
                try:
                    body = self._body()
                    if self.path == "/api/review":
                        if not isinstance(body, dict) or body.get("project_id") != load_model(state.model_path).get("project", {}).get("id"):
                            raise ValueError("review project does not match the served model")
                        body["saved_at"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
                        atomic_write(state.output_directory / "review-decisions.json", (json.dumps(body, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
                        self._json(HTTPStatus.OK, {"saved": True})
                        return
                    if self.path == "/api/chat":
                        result = state.bridge.chat(str(body.get("message", "")), body.get("review"))
                        self._json(HTTPStatus.OK, result)
                        return
                    self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})
                except PermissionError as exc:
                    self._json(HTTPStatus.FORBIDDEN, {"error": str(exc)})
                except (ValueError, json.JSONDecodeError) as exc:
                    self._json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
                except subprocess.TimeoutExpired:
                    self._json(HTTPStatus.GATEWAY_TIMEOUT, {"error": "Claude bridge timed out without applying a revision."})
                except Exception as exc:
                    self._json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)[:2000]})

            def _authorized(self) -> bool:
                supplied = self.headers.get("X-Arch-Studio-Token", "")
                if not secrets.compare_digest(supplied, state.token):
                    self._json(HTTPStatus.FORBIDDEN, {"error": "invalid review token"})
                    return False
                origin = self.headers.get("Origin")
                if origin:
                    parsed = urlparse(origin)
                    if parsed.netloc != self.headers.get("Host") or parsed.scheme != "http":
                        self._json(HTTPStatus.FORBIDDEN, {"error": "origin rejected"})
                        return False
                return True

            def _body(self) -> dict[str, Any]:
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                except ValueError as exc:
                    raise ValueError("invalid content length") from exc
                if length <= 0 or length > MAX_BODY:
                    raise ValueError(f"request body must be between 1 and {MAX_BODY} bytes")
                body = json.loads(self.rfile.read(length).decode("utf-8"))
                if not isinstance(body, dict):
                    raise ValueError("request body must be a JSON object")
                return body

            def _json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
                self._bytes(status, json.dumps(payload, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

            def _bytes(self, status: HTTPStatus, content: bytes, content_type: str) -> None:
                self.send_response(status)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(content)))
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("Referrer-Policy", "no-referrer")
                self.send_header("X-Frame-Options", "DENY")
                self.end_headers()
                self.wfile.write(content)

        self.httpd = ThreadingHTTPServer(("127.0.0.1", self.port), Handler)
        actual_port = self.httpd.server_address[1]
        url = f"http://127.0.0.1:{actual_port}/"
        print(f"Arch Studio review: {url}", flush=True)
        print(f"Claude bridge: {'enabled' if self.bridge.enabled else 'disabled'}", flush=True)
        print("Press Ctrl-C to stop.", flush=True)
        if open_browser:
            threading.Timer(0.25, lambda: webbrowser.open(url)).start()
        try:
            self.httpd.serve_forever(poll_interval=0.25)
        except KeyboardInterrupt:
            pass
        finally:
            self.httpd.server_close()
