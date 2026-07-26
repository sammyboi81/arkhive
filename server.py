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

from core import birth, remember, recall, verify, govern  # ONE source of truth — see core.py

# ---------------- MCP surface ----------------
VERSION = "0.1.1"

TOOLS = [
    {
        "name": "birth",
        "description": "Earn an identity (Law 5: born, not configured) before acting.",
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
        "description": "Write a tamper-evident record. Requires a born soul_id as actor.",
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
        "description": "Read prior context so the AI need not re-derive it.",
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
        "description": "Prove the entire memory chain is unbroken.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "govern",
        "description": "Ask whether an action may proceed using deterministic rules.",
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
                "instructions": "Governed, tamper-evident local memory for AI assistants.",
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
