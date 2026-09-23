#!/usr/bin/env python3
"""project-bridge — minimal MCP stdio server (JSON-RPC 2.0).

Deterministic coordination tools only. No LLM calls. Offline.
Protocol: MCP initialize / tools/list / tools/call / ping / notifications.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

# Ensure sibling import works when launched with absolute path
sys.path.insert(0, str(Path(__file__).resolve().parent))

import bridge  # noqa: E402

PROTOCOL_VERSION = "2024-11-05"
SERVER_INFO = {"name": "project-bridge", "version": bridge.bridge_version()}

TOOLS: list[dict[str, Any]] = [
    {
        "name": "project_status",
        "description": (
            "Compact multi-agent project status: branch, HEAD, working tree, "
            "active claims, recent changes, decisions. Prefer this at session start. "
            "Git remains authoritative for code."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "agent": {
                    "type": "string",
                    "enum": ["codex", "opencode", "agy", "unknown"],
                    "description": "Override agent identity (optional; auto-detected)",
                }
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "recent_changes",
        "description": "List recent recorded coordination changes (default limit 5).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "minimum": 1, "maximum": 50},
                "since": {"type": "string", "description": "ISO timestamp lower bound"},
                "path": {"type": "string", "description": "Repo-relative path filter"},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "record_change",
        "description": (
            "Record what you changed: summary, files, tests run, decisions, issues, "
            "next_action. Do not include secrets or full file contents. "
            "Call after meaningful work."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "agent": {"type": "string"},
                "task": {"type": "string"},
                "summary": {"type": "string"},
                "files": {"type": "array", "items": {"type": "string"}},
                "tests": {"type": "array", "items": {"type": "string"}},
                "decisions": {"type": "array", "items": {"type": "string"}},
                "issues": {"type": "array", "items": {"type": "string"}},
                "next_action": {"type": "string"},
                "auto": {
                    "type": "boolean",
                    "description": "If true, fill empty fields from git status only",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "claim_task",
        "description": (
            "Advisory claim on a task/scope so other agents see a conflict warning. "
            "Does not hard-block work. TTL prevents stale locks."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "task": {"type": "string"},
                "scope": {"type": "array", "items": {"type": "string"}},
                "agent": {"type": "string"},
                "ttl_seconds": {"type": "integer", "minimum": 60, "maximum": 86400},
            },
            "required": ["task"],
            "additionalProperties": False,
        },
    },
    {
        "name": "release_task",
        "description": "Release a previously claimed task.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task": {"type": "string"},
                "agent": {"type": "string"},
            },
            "required": ["task"],
            "additionalProperties": False,
        },
    },
    {
        "name": "active_tasks",
        "description": "List non-expired task claims from all agents.",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
    {
        "name": "get_decisions",
        "description": "List recent recorded technical decisions.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "minimum": 1, "maximum": 50},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "record_decision",
        "description": "Record a short durable technical decision (title + optional detail).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "detail": {"type": "string"},
                "agent": {"type": "string"},
            },
            "required": ["title"],
            "additionalProperties": False,
        },
    },
    {
        "name": "request_handoff",
        "description": "Leave a bounded structured task for another known agent. Does not start or spawn an agent.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "to_agent": {"type": "string", "enum": ["codex", "opencode", "agy"]},
                "type": {"type": "string", "enum": ["review", "implement", "investigate", "test", "second_opinion"]},
                "task": {"type": "string", "maxLength": 200},
                "title": {"type": "string", "maxLength": 200},
                "summary": {"type": "string", "maxLength": 4096},
                "scope": {"type": "array", "items": {"type": "string"}, "maxItems": 50},
                "priority": {"type": "string", "enum": ["low", "normal", "high"]},
                "base_commit": {"type": "string"},
            },
            "required": ["to_agent", "type", "task", "title", "summary"],
            "additionalProperties": False,
        },
    },
    {
        "name": "get_handoffs",
        "description": "List the current agent's incoming handoffs by default, or filter by status, recipient, sender, id and limit.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["pending", "accepted", "in_progress", "completed", "declined", "cancelled"]},
                "to_agent": {"type": "string", "enum": ["codex", "opencode", "agy"]},
                "from_agent": {"type": "string", "enum": ["codex", "opencode", "agy"]},
                "handoff_id": {"type": "string"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 50},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "accept_handoff",
        "description": "Atomically accept a pending handoff assigned to the current agent.",
        "inputSchema": {
            "type": "object",
            "properties": {"handoff_id": {"type": "string"}},
            "required": ["handoff_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "complete_handoff",
        "description": "Complete an accepted handoff with a concise structured result. Record code changes separately with record_change.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "handoff_id": {"type": "string"},
                "summary": {"type": "string", "maxLength": 4096},
                "outcome": {"type": "string", "maxLength": 200},
                "findings": {"type": "array", "maxItems": 50, "items": {"type": "object"}},
                "tests": {"type": "array", "maxItems": 50, "items": {"type": "string"}},
                "recommended_action": {"type": "string", "maxLength": 2048},
            },
            "required": ["handoff_id", "summary", "outcome"],
            "additionalProperties": False,
        },
    },
    {
        "name": "cancel_handoff",
        "description": "Cancel a pending, accepted or in-progress handoff as one of its two participants.",
        "inputSchema": {
            "type": "object",
            "properties": {"handoff_id": {"type": "string"}, "reason": {"type": "string", "maxLength": 500}},
            "required": ["handoff_id"],
            "additionalProperties": False,
        },
    },
]


def _root() -> Path:
    # Prefer env from hook; else discover from cwd / script location
    env_root = os.environ.get("PROJECT_BRIDGE_ROOT")
    if env_root and Path(env_root).is_dir():
        return Path(env_root).resolve()
    # script lives at <root>/.agents/project-bridge/server.py
    candidate = Path(__file__).resolve().parents[2]
    if (candidate / ".git").exists() or (candidate / "AGENTS.md").exists():
        return candidate
    return bridge.repo_root()


ROOT = _root()


def _text_result(payload: Any) -> dict[str, Any]:
    if isinstance(payload, str):
        text = payload
    else:
        try:
            text = json.dumps(payload, ensure_ascii=False, indent=2)
        except (TypeError, ValueError):
            text = str(payload)
    # Keep normal status compact, while allowing one structured result to be
    # inspected without silently dropping its findings.
    if len(text) > 16000:
        text = text[:15990] + "\n…truncated"
    return {"content": [{"type": "text", "text": text}], "isError": False}


def _err_result(message: str) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": message}], "isError": True}


def call_tool(name: str, args: dict[str, Any]) -> dict[str, Any]:
    try:
        if name == "project_status":
            return _text_result(bridge.project_status(ROOT, args.get("agent")))
        if name == "recent_changes":
            return _text_result(
                bridge.recent_changes(
                    ROOT,
                    limit=args.get("limit"),
                    since=args.get("since"),
                    path=args.get("path"),
                )
            )
        if name == "record_change":
            return _text_result(
                bridge.record_change(
                    ROOT,
                    agent=args.get("agent"),
                    task=args.get("task") or "",
                    summary=args.get("summary") or "",
                    files=args.get("files"),
                    tests=args.get("tests"),
                    decisions=args.get("decisions"),
                    issues=args.get("issues"),
                    next_action=args.get("next_action") or "",
                    auto=bool(args.get("auto")),
                )
            )
        if name == "claim_task":
            return _text_result(
                bridge.claim_task(
                    ROOT,
                    task=args.get("task") or "",
                    scope=args.get("scope"),
                    agent=args.get("agent"),
                    ttl_seconds=args.get("ttl_seconds"),
                )
            )
        if name == "release_task":
            return _text_result(
                bridge.release_task(
                    ROOT, task=args.get("task") or "", agent=args.get("agent")
                )
            )
        if name == "active_tasks":
            return _text_result(bridge.active_tasks(ROOT))
        if name == "get_decisions":
            return _text_result(bridge.get_decisions(ROOT, limit=args.get("limit") or 10))
        if name == "record_decision":
            return _text_result(
                bridge.record_decision(
                    ROOT,
                    title=args.get("title") or "",
                    detail=args.get("detail") or "",
                    agent=args.get("agent"),
                )
            )
        if name == "request_handoff":
            return _text_result(
                bridge.request_handoff(
                    ROOT,
                    to_agent=args.get("to_agent") or "",
                    type=args.get("type") or "",
                    task=args.get("task") or "",
                    title=args.get("title") or "",
                    summary=args.get("summary") or "",
                    scope=args.get("scope"),
                    priority=args.get("priority") or "normal",
                    base_commit=args.get("base_commit"),
                )
            )
        if name == "get_handoffs":
            return _text_result(
                bridge.get_handoffs(
                    ROOT,
                    status=args.get("status"),
                    to_agent=args.get("to_agent"),
                    from_agent=args.get("from_agent"),
                    limit=args.get("limit"),
                    handoff_id=args.get("handoff_id"),
                )
            )
        if name == "accept_handoff":
            return _text_result(bridge.accept_handoff(ROOT, args.get("handoff_id") or ""))
        if name == "complete_handoff":
            return _text_result(
                bridge.complete_handoff(
                    ROOT,
                    handoff_id=args.get("handoff_id") or "",
                    summary=args.get("summary") or "",
                    outcome=args.get("outcome") or "",
                    findings=args.get("findings"),
                    tests=args.get("tests"),
                    recommended_action=args.get("recommended_action") or "",
                )
            )
        if name == "cancel_handoff":
            return _text_result(
                bridge.cancel_handoff(
                    ROOT,
                    handoff_id=args.get("handoff_id") or "",
                    reason=args.get("reason") or "",
                )
            )
        return _err_result(f"Unknown tool: {name}")
    except Exception as exc:  # noqa: BLE001 — MCP must not crash the host
        return _err_result(f"project-bridge error: {type(exc).__name__}: {exc}")


def handle(req: dict[str, Any]) -> dict[str, Any] | None:
    """Return a JSON-RPC response dict, or None for notifications."""
    rid = req.get("id")
    method = req.get("method")
    params = req.get("params") or {}

    if method is None:
        return None

    # notifications
    if str(method).startswith("notifications/"):
        return None

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": rid,
            "result": {
                "protocolVersion": params.get("protocolVersion", PROTOCOL_VERSION),
                "capabilities": {"tools": {}},
                "serverInfo": SERVER_INFO,
            },
        }

    if method == "ping":
        return {"jsonrpc": "2.0", "id": rid, "result": {}}

    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": rid, "result": {"tools": TOOLS}}

    if method == "tools/call":
        name = params.get("name") or ""
        args = params.get("arguments") or {}
        if not isinstance(args, dict):
            args = {}
        result = call_tool(name, args)
        return {"jsonrpc": "2.0", "id": rid, "result": result}

    # method not found
    return {
        "jsonrpc": "2.0",
        "id": rid,
        "error": {"code": -32601, "message": f"Method not found: {method}"},
    }


def main() -> None:
    # Line-delimited JSON-RPC over stdio (MCP stdio transport)
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(req, dict):
            continue
        resp = handle(req)
        if resp is not None:
            sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
