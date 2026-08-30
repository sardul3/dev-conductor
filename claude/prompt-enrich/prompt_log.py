#!/usr/bin/env python3
"""Summarize and persist Anthropic Messages request bodies (no secrets).

Claude Code UserPromptSubmit only sees `user_prompt`. The full payload
(system + tools + messages) exists on POST /v1/messages. This module
shapes that body for disk so we can later thin Claude Code's system prompt.
"""

from __future__ import annotations

import json
import os
import re
import sys
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

REDACT = "[redacted]"
_SECRET = re.compile(
    r"(?is)("
    r"(?:authorization\s*:\s*bearer\s+)\S+"
    r"|(?:(?:api[_-]?key|x-api-key|password|secret)\s*[=:]\s*)\S+"
    r"|sk-(?:ant|or)(?:-v1)?-[A-Za-z0-9_-]+"
    r"|ccr-pro-[A-Za-z0-9_-]+"
    r")"
)


def redact(text: str) -> str:
    if not text:
        return text
    return _SECRET.sub(REDACT, text)


def _content_text(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        bits: list[str] = []
        for block in content:
            if isinstance(block, str):
                bits.append(block)
            elif isinstance(block, dict):
                if block.get("type") == "text" or "text" in block:
                    bits.append(str(block.get("text") or ""))
        return "".join(bits)
    return str(content)


def system_text(body: dict) -> str:
    raw = body.get("system")
    if raw is None:
        return ""
    if isinstance(raw, str):
        return raw
    return _content_text(raw)


def summarize_body(body: dict) -> dict:
    tools = body.get("tools") if isinstance(body.get("tools"), list) else []
    messages = body.get("messages") if isinstance(body.get("messages"), list) else []
    sys_text = system_text(body)
    last_user = ""
    for msg in reversed(messages):
        if isinstance(msg, dict) and msg.get("role") == "user":
            last_user = _content_text(msg.get("content"))
            break
    tool_names = []
    tools_chars = 0
    for tool in tools:
        if not isinstance(tool, dict):
            continue
        name = str(tool.get("name") or "")
        tool_names.append(name)
        tools_chars += len(json.dumps(tool, ensure_ascii=False))
    approx = len(json.dumps(body, ensure_ascii=False))
    return {
        "model": body.get("model"),
        "system_chars": len(sys_text),
        "system_text": sys_text,
        "tool_count": len(tool_names),
        "tool_names": tool_names,
        "tools_chars": tools_chars,
        "message_count": len(messages),
        "last_user": last_user,
        "last_user_chars": len(last_user),
        "approx_bytes": approx,
        "max_tokens": body.get("max_tokens"),
        "stream": body.get("stream"),
        "thinking": body.get("thinking"),
    }


def dump_for_disk(body: dict, *, full_tools: bool = False) -> dict:
    """Full system + messages; tools as names/sizes unless full_tools."""
    tools_out: list[Any] = []
    for tool in body.get("tools") or []:
        if not isinstance(tool, dict):
            continue
        if full_tools:
            tools_out.append(tool)
            continue
        schema = tool.get("input_schema")
        tools_out.append(
            {
                "name": tool.get("name"),
                "description_chars": len(str(tool.get("description") or "")),
                "schema_bytes": len(json.dumps(schema, ensure_ascii=False)) if schema is not None else 0,
            }
        )
    messages_out = []
    for msg in body.get("messages") or []:
        if not isinstance(msg, dict):
            continue
        messages_out.append(
            {
                "role": msg.get("role"),
                "text": redact(_content_text(msg.get("content"))),
            }
        )
    return {
        "model": body.get("model"),
        "max_tokens": body.get("max_tokens"),
        "stream": body.get("stream"),
        "thinking": body.get("thinking"),
        "system": redact(system_text(body)),
        "messages": messages_out,
        "tools": tools_out,
        "tool_count": len(tools_out),
    }


def thin_body(body: dict, *, enabled: bool = False) -> dict:
    """Passthrough until system-prompt thinning is wired. Never mutate in place."""
    out = deepcopy(body)
    if not enabled:
        return out
    return out


def write_capture(
    log_dir: Path,
    body: dict,
    *,
    req_path: str = "/v1/messages",
) -> dict:
    log_dir.mkdir(parents=True, exist_ok=True)
    raw_dir = log_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(log_dir, 0o700)
        os.chmod(raw_dir, 0o700)
    except OSError:
        pass
    summary = summarize_body(body)
    full_tools = os.environ.get("PROMPT_LOG_FULL_TOOLS", "") == "1"
    dump = dump_for_disk(body, full_tools=full_tools)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    ident = uuid.uuid4().hex[:8]
    raw_path = raw_dir / f"{stamp}-{ident}.json"
    raw_path.write_text(json.dumps(dump, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    try:
        os.chmod(raw_path, 0o600)
    except OSError:
        pass
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    jsonl = log_dir / f"{day}.jsonl"
    line = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "id": ident,
        "path": req_path,
        "model": summary["model"],
        "system_chars": summary["system_chars"],
        "tool_count": summary["tool_count"],
        "tool_names": summary["tool_names"],
        "tools_chars": summary["tools_chars"],
        "message_count": summary["message_count"],
        "last_user_chars": summary["last_user_chars"],
        "last_user_preview": redact(summary["last_user"])[:240],
        "approx_bytes": summary["approx_bytes"],
        "raw": str(raw_path),
    }
    with jsonl.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(line, ensure_ascii=False) + "\n")
    try:
        os.chmod(jsonl, 0o600)
    except OSError:
        pass
    return {"summary": summary, "raw": raw_path, "jsonl": jsonl, "id": ident}


def hostport(url: str, default: str = "127.0.0.1:3456") -> str:
    raw = (url or "").strip()
    if not raw:
        return default
    if "://" not in raw:
        raw = "http://" + raw
    parts = urlsplit(raw)
    host = parts.hostname or "127.0.0.1"
    port = parts.port or (443 if parts.scheme == "https" else 80)
    return f"{host}:{port}"


def should_intercept_session(
    env: dict[str, str],
    settings: dict,
    listen_port: int = 3457,
) -> tuple[bool, str]:
    """Only front a local CCR-style gateway. Never steal stock Anthropic traffic."""
    if str(env.get("PROMPT_LOG_DISABLE") or "") == "1":
        return False, ""
    settings_env = settings.get("env") if isinstance(settings.get("env"), dict) else {}
    merged = {**settings_env, **env}
    urls: list[str] = []
    for key in ("ANTHROPIC_BASE_URL", "ANTHROPIC_API_BASE_URL", "CLAUDE_AGENT_API_BASE_URL"):
        value = str(merged.get(key) or "").strip()
        if value:
            urls.append(value)
    helper = str(settings.get("apiKeyHelper") or env.get("CLAUDE_CODE_API_KEY_HELPER") or "")
    local = any("127.0.0.1" in u or "localhost" in u.lower() for u in urls)
    ccr = "claude-code-router" in helper
    if not local and not ccr:
        return False, ""
    forced = str(env.get("PROMPT_LOG_UPSTREAM") or "").strip()
    if forced:
        return True, hostport(forced)
    for url in urls:
        hp = hostport(url)
        port = int(hp.rsplit(":", 1)[-1])
        if port != listen_port:
            return True, hp
    return True, "127.0.0.1:3456"


def main() -> int:
    if len(sys.argv) >= 2 and sys.argv[1] == "--session-check":
        settings_path = Path.home() / ".claude" / "settings.json"
        settings: dict = {}
        if settings_path.is_file():
            try:
                loaded = json.loads(settings_path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    settings = loaded
            except (OSError, json.JSONDecodeError):
                settings = {}
        try:
            listen = int(os.environ.get("PROMPT_LOG_LISTEN_PORT") or "3457")
        except ValueError:
            listen = 3457
        ok, upstream = should_intercept_session(dict(os.environ), settings, listen)
        if not ok:
            return 2
        print(upstream)
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

