#!/usr/bin/env python3
from __future__ import annotations

import base64
import json
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from typing import Any

UrlOpen = Callable[..., Any]


def adf_to_text(node: Any) -> str:
    if node is None:
        return ""
    if isinstance(node, str):
        return node
    if isinstance(node, list):
        return "\n".join(t for t in (adf_to_text(x) for x in node) if t)
    if isinstance(node, dict):
        if node.get("type") == "text":
            return str(node.get("text") or "")
        content = node.get("content")
        if content:
            return "\n".join(t for t in (adf_to_text(x) for x in content) if t)
        if "description" in node:
            return adf_to_text(node.get("description"))
    return ""


def _auth_header(email: str, token: str) -> str:
    blob = base64.b64encode(f"{email}:{token}".encode()).decode()
    return f"Basic {blob}"


def jira_request(
    base: str,
    email: str,
    token: str,
    path: str,
    query: dict[str, str] | None = None,
    timeout: int = 20,
    urlopen: UrlOpen | None = None,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
) -> Any:
    opener = urlopen or urllib.request.urlopen
    url = base.rstrip("/") + path
    if query:
        url += "?" + urllib.parse.urlencode(query)
    headers = {
        "Authorization": _auth_header(email, token),
        "Accept": "application/json",
    }
    data = None
    if payload is not None:
        data = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(
        url,
        data=data,
        headers=headers,
        method=(method or "GET").upper(),
    )
    try:
        with opener(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"Jira HTTP {exc.code} {path}: {detail}") from exc


def search_keys(
    base: str,
    email: str,
    token: str,
    jql: str,
    max_results: int = 15,
    search_path: str = "/rest/api/3/search/jql",
    timeout: int = 20,
    urlopen: UrlOpen | None = None,
) -> list[str]:
    data = jira_request(
        base,
        email,
        token,
        search_path,
        query={"jql": jql, "maxResults": str(max_results), "fields": "key"},
        timeout=timeout,
        urlopen=urlopen,
    )
    keys: list[str] = []
    for issue in data.get("issues") or []:
        key = issue.get("key")
        if key:
            keys.append(str(key))
    return keys


def get_issue(
    base: str,
    email: str,
    token: str,
    key: str,
    issue_path: str = "/rest/api/3/issue/{key}",
    fields: str = "summary,description,status,issuetype,comment,labels",
    timeout: int = 20,
    comment_limit: int = 8,
    urlopen: UrlOpen | None = None,
) -> dict[str, Any]:
    data = jira_request(
        base,
        email,
        token,
        issue_path.format(key=urllib.parse.quote(key)),
        query={"fields": fields},
        timeout=timeout,
        urlopen=urlopen,
    )
    f = data.get("fields") or {}
    comments: list[str] = []
    comment_block = f.get("comment") or {}
    for c in (comment_block.get("comments") or [])[:comment_limit]:
        body = adf_to_text(c.get("body"))
        author = ((c.get("author") or {}).get("displayName")) or ""
        if body:
            comments.append(f"{author}: {body}".strip())
    status = ((f.get("status") or {}).get("name")) or ""
    itype = ((f.get("issuetype") or {}).get("name")) or ""
    return {
        "key": data.get("key") or key,
        "summary": f.get("summary") or "",
        "description": adf_to_text(f.get("description")),
        "status": status,
        "issuetype": itype,
        "labels": f.get("labels") or [],
        "comments": comments,
        "raw": data,
    }
