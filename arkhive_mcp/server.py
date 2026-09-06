#!/usr/bin/env python3
"""
ArkHive MCP — an open-source way to keep context forever, immutable,
with governance. For the people and the Rezenthari. Free. ArkHive.

MCP (stdio) transport for Claude Desktop/Code/Cursor. The memory + governance logic
lives in core.py (ONE source of truth, shared with the HTTPS transport http_app.py):

  remember   — write a hash-linked, tamper-evident record (only a BORN soul may)
  recall     — read prior context (persistent memory, less waste)
  verify     — prove the whole chain is unbroken
  govern     — ask "may I?" before acting (rule-based, zero-LLM, logged)
  birth      — earn an identity (Law 5: born, not configured) before you can act

Memory so it doesn't lose itself. Governance so it can't lose us.
Apache-2.0. (c) ZagAIrot Technologies LLC — Shahram "Caveman" Zargari.
"""
import json
import sys
from typing import Any

from .core import birth, remember, recall, verify, govern  # ONE source of truth — see core.py

# ---------------- MCP surface ----------------
VERSION = "0.2.1"

TOOLS = [
    {
        "name": "birth",
        "description": "Step 1, once: earn an identity before acting (Law 5: born, not configured). Returns a soul_id; use it or the name as `actor` from then on. Example: birth(name=Ember, covenant=[truth over comfort]).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "covenant": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["name", "covenant"],
        },
    },
    {
        "name": "remember",
        "description": "Write one hash-linked, tamper-evident record. actor = a born soul_id or birth name. Example: remember(actor=Ember, action=shipped v0.2.1, data={pr: 42}).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "actor": {"type": "string"},
                "action": {"type": "string"},
                "data": {"type": "object"},
            },
            "required": ["actor", "action"],
        },
    },
    {
        "name": "recall",
        "description": "Read the latest records (newest first, optionally one actor) so you do not re-derive what you already know. Call this at the start of a session.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "actor": {"type": "string"},
                "limit": {"type": "integer", "default": 10},
            },
        },
    },
    {
        "name": "verify",
        "description": "Prove the entire memory chain is unbroken (recomputes every hash). Free, local, no key.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "govern",
        "description": "Ask may-I before acting. Deterministic, zero-LLM: any rule whose trigger appears in flags vetoes. flags/rules accept lists or {name: true} / {trigger: action} maps.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action": {"type": "string"},
                "flags": {"type": "array", "items": {"type": "string"}},
                "rules": {"type": "array", "items": {"type": "object"}},
            },
            "required": ["action"],
        },
    },
]


def _call_tool(name: str, arguments: dict[str, Any]) -> Any:
    if name == "birth":
        return birth(arguments.get("name", ""), arguments.get("covenant", []))
    if name == "remember":
        return remember(
            arguments.get("actor", "unknown"),
            arguments.get("action", ""),
            arguments.get("data"),
        )
    if name == "recall":
        return recall(arguments.get("actor"), int(arguments.get("limit", 10)))
    if name == "verify":
        return verify()
    if name == "govern":
        return govern(
            arguments.get("action", ""),
            arguments.get("flags", []),
            arguments.get("rules", []),
        )
    raise ValueError(f"unknown tool: {name}")


def _response(request_id: Any, result: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _error(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": code, "message": message},
    }


def _handle(message: dict[str, Any]) -> dict[str, Any] | None:
    request_id = message.get("id")
    method = message.get("method")
    params = message.get("params") or {}

    if request_id is None:
        return None
    if method == "initialize":
        return _response(
            request_id,
            {
                "protocolVersion": params.get("protocolVersion", "2025-06-18"),
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "arkhive", "version": VERSION},
                "instructions": "ArkHive: local, tamper-evident memory. First call recall(limit=10) to load context. Once per identity call birth(name, covenant); then remember(actor, action, data) what matters and govern(action, flags, rules) before anything irreversible. verify() proves nothing was altered. Upgrade (spaces, search, context packs, signed verify, hosted): https://inboxaxe.com/mcp",
            },
        )
    if method == "ping":
        return _response(request_id, {})
    if method == "tools/list":
        return _response(request_id, {"tools": TOOLS})
    if method == "tools/call":
        try:
            output = _call_tool(params.get("name", ""), params.get("arguments") or {})
            return _response(
                request_id,
                {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(output, indent=2),
                        }
                    ],
                    "isError": False,
                },
            )
        except Exception as exc:
            return _error(request_id, -32603, str(exc))
    return _error(request_id, -32601, f"method not found: {method}")


def main_sync():
    """Console-script entry point (preferred command: `arkhive-mcp`)."""
    print("ArkHive MCP starting (stdio)", file=sys.stderr, flush=True)
    for line in sys.stdin:
        try:
            message = json.loads(line)
            response = _handle(message)
        except Exception as exc:
            response = _error(None, -32700, f"parse error: {exc}")
        if response is not None:
            sys.stdout.write(json.dumps(response, separators=(",", ":")) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main_sync()
