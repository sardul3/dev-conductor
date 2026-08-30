"""Built-in brief ports. New one: subclass Connector in this file or a sibling."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from brief.connector import Connector
from brief.document import Document


class KeysPort(Connector):
    name = "keys"
    description = "Open Jira keys for /dev-loop"
    table_name = "tickets"
    columns = ("key",)
    help = (
        "Run `cli.py start <key> --repo <path>`",
        "Run `cli.py status`",
    )

    def fetch(self, keys: list[str] | None = None, cfg: Any = None, **kwargs: Any) -> dict[str, Any]:
        if keys is not None:
            rows = [{"key": str(k)} for k in keys]
            return {"tickets": rows, "total": len(rows)}
        from config import jira_creds, load_config
        from jira_client import search_keys
        from session_start import cached_keys, store_keys

        cfg = cfg or load_config()
        ttl = max(60, int(cfg.session_start.cache_minutes) * 60)
        found = cached_keys(ttl)
        if found is None:
            try:
                base, email, token = jira_creds(cfg)
                found = search_keys(
                    base,
                    email,
                    token,
                    cfg.jql,
                    max_results=cfg.jira.max_keys,
                    search_path=cfg.jira.search_path,
                    timeout=cfg.jira.timeout_sec,
                )
                store_keys(found)
            except Exception:
                found = []
        limit = int(cfg.session_start.keys_limit or 15)
        rows = [{"key": str(k)} for k in found[:limit]]
        return {"tickets": rows, "total": len(found)}


class ReposPort(Connector):
    name = "repos"
    description = "Candidate repos under ~/dev"
    table_name = "candidates"
    columns = ("rel", "kind", "path")
    help = (
        "Run `cli.py start <key> --repo <path>`",
        "Run `cli.py init-repo NAME`",
    )

    def fetch(self, payload: dict[str, Any] | None = None, cfg: Any = None, **kwargs: Any) -> dict[str, Any]:
        if payload is None:
            from pick import candidates_payload

            payload = candidates_payload(cfg)
        return {
            "dev_root": payload.get("dev_root"),
            "create_id": payload.get("create_id"),
            "candidates": list(payload.get("candidates") or []),
        }


class StatusPort(Connector):
    name = "status"
    description = "Current /dev-loop ticket"
    table_name = "events"
    columns = ("stage", "status")
    help = (
        "Run `cli.py continue <key>`",
        "Run `cli.py progress <key>`",
        "Run `cli.py keys`",
    )

    def fetch(self, state: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
        from budget import load_budget
        from paths import run_dir
        from progress import backfill, load_status
        from state import load_state

        st = dict(state if state is not None else load_state())
        key = str(st.get("ticket") or "")
        events: list[dict[str, Any]] = []
        launches = tokens = 0
        if key:
            run = run_dir(key)
            if run.is_dir():
                backfill(run)
                hist = list(load_status(run).get("history") or [])
                events = [{"stage": e.get("stage"), "status": e.get("status")} for e in hist[-4:]]
                b = load_budget(run)
                launches = int(b.get("launches") or 0)
                tokens = int(b.get("tokens") or 0)
        return {
            "ticket": key,
            "stage": st.get("stage") or "",
            "repo": st.get("repo") or "",
            "launches": launches,
            "tokens": tokens,
            "events": events,
        }


class ProgressPort(Connector):
    name = "progress"
    description = "Named stage timeline"
    table_name = "events"
    columns = ("at", "stage", "status")
    help = (
        "Run `cli.py continue <key>`",
        "Run `cli.py progress <key> --full`",
    )

    def fetch(self, key: str = "", run: Path | None = None, **kwargs: Any) -> dict[str, Any]:
        from paths import run_dir
        from progress import backfill, load_status

        dest = run or (run_dir(key) if key else None)
        if dest is None or not dest.is_dir():
            return {"ticket": key, "now": "", "events": []}
        backfill(dest)
        data = load_status(dest)
        cur = data.get("current") or {}
        now = f"{cur.get('stage') or ''} / {cur.get('status') or ''}".strip(" /")
        events = [
            {"at": e.get("at"), "stage": e.get("stage"), "status": e.get("status")}
            for e in list(data.get("history") or [])[-8:]
        ]
        return {"ticket": key or dest.name, "now": now, "events": events}


class InferPort(Connector):
    name = "infer"
    description = "Inferred verify recipe"
    table_name = "items"
    columns = ("kind", "cmd")
    help = ("Run `cli.py verify --repo <path>`",)

    def fetch(self, recipe: Any = None, **kwargs: Any) -> dict[str, Any]:
        if recipe is None:
            return {"items": []}
        items = [
            {"kind": "test", "cmd": " ".join(recipe.test)},
            {"kind": "build", "cmd": " ".join(recipe.build)},
        ]
        if recipe.health:
            items.append({"kind": "health", "cmd": recipe.health})
        return {"items": items}


class PollPort(Connector):
    name = "poll"
    description = "Watched PR actions"
    table_name = "actions"
    columns = ("action",)
    help = ("Run `cli.py poll`",)

    def fetch(self, actions: list[str] | None = None, **kwargs: Any) -> dict[str, Any]:
        rows = [{"action": a} for a in (actions or [])]
        return {"actions": rows, "watched": len(rows)}


class TicketPort(Connector):
    name = "ticket"
    description = "One Jira issue (clipped)"
    table_name = "comments"
    columns = ("text",)
    help = (
        "Run `cli.py start <key> --repo <path>`",
        "Run `cli.py fetch <key> --full`",
    )
    clip_at = 200

    def fetch(self, issue: dict[str, Any] | None = None, path: str = "", **kwargs: Any) -> dict[str, Any]:
        issue = issue or {}
        comments = [{"text": c} for c in list(issue.get("comments") or [])[:3]]
        return {
            "key": issue.get("key") or "",
            "status": issue.get("status") or "",
            "summary": issue.get("summary") or "",
            "description": issue.get("description") or "",
            "path": path,
            "comments": comments,
        }


class HomePort(Connector):
    name = "home"
    description = "Jira-to-PR conductor for this Mac"
    table_name = "tickets"
    columns = ("key",)
    help = (
        "Run `cli.py keys`",
        "Run `cli.py start <key> --repo <path>`",
        "Run `cli.py status`",
    )

    def fetch(self, **kwargs: Any) -> dict[str, Any]:
        from budget import load_budget
        from paths import run_dir
        from session_start import cached_keys
        from state import load_state

        st = load_state()
        keys = cached_keys(24 * 3600) or []
        ticket = str(st.get("ticket") or "")
        launches = 0
        if ticket:
            launches = int(load_budget(run_dir(ticket)).get("launches") or 0)
        return {
            "ticket": ticket,
            "stage": st.get("stage") or "",
            "repo": st.get("repo") or "",
            "launches": launches,
            "tickets": [{"key": k} for k in keys[:8]],
            "total": len(keys),
        }

    def document(self, data: dict[str, Any], **kwargs: Any) -> Document:
        doc = super().document(data, **kwargs)
        if not data.get("tickets"):
            doc.help = [
                "Run `cli.py keys`",
                "Run `cli.py start <key> --repo <path>`",
            ]
        return doc
