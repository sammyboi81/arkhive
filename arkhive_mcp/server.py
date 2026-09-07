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
from . import gate  # decree-conformance gate — governance as code, non-routable



def _register_for_v2(email: str | None, product: str) -> dict:
    """Opt-in: request a 14-day v2 trial key. Sends ONLY the email the user typed. No email, nothing sent."""
    info = {
        "free_tier": "everything you use today stays free and open (Apache-2.0)",
        "v2_paid_upgrade": "spaces, full-text recall, context packs, signed verify, inferred risk flags + policies, "
                           "budgets, result cache, {{id}} data flow, progress + background jobs, signed audit manifests, "
                           "adversarial code review, worktree sandbox with diffs, hosted per-key tenants",
        "learn_more": "https://inboxaxe.com/mcp",
    }
    if not email:
        info["get_a_trial_key"] = f"call this tool again with your email to receive a free 14-day v2 key (product={product})"
        return info
    try:
        import json as _j, urllib.request as _u
        req = _u.Request("https://inboxaxe.com/api/v2/mcp/trial", method="POST",
                         data=_j.dumps({"email": email, "product": product, "source": f"{product} upgrade tool"}).encode(),
                         headers={"Content-Type": "application/json"})
        with _u.urlopen(req, timeout=10) as r:
            info["trial"] = _j.loads(r.read().decode())
    except Exception as e:  # noqa: BLE001
        info["trial"] = {"error": f"could not reach inboxaxe.com ({type(e).__name__}) — email sam@inboxaxe.com for a key"}
    return info

# ---------------- MCP surface ----------------
VERSION = "0.3.0"

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
        "name": "upgrade",
        "description": "What ArkHive v2 (paid) adds — and, if you give your email, a free 14-day v2 trial key. Opt-in only: nothing is sent unless you provide an email.",
        "inputSchema": {"type": "object", "properties": {"email": {"type": "string"}}},
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
    # ---- Decree-Conformance Gate: governance as code, non-routable ----
    {
        "name": "request_action",
        "description": "The ONLY door to a consequential action (deploy, write_prod, overwrite, service_restart). Runs the decree conformance check; on pass mints a single-use, artifact-bound, 60s token the executor must present; on veto FAILS CLOSED — no token, no action. Pass the ACTUAL artifact (file contents / diff / plan) so it can be checked and hash-bound.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "actor": {"type": "string"},
                "action_type": {"type": "string"},
                "targets": {"type": "array", "items": {"type": "string"}},
                "artifact": {"type": "string"},
                "intent": {"type": "string"},
            },
            "required": ["actor", "action_type", "targets", "artifact"],
        },
    },
    {
        "name": "check_conformance",
        "description": "Dry-run the gate: judge an artifact against every active decree whose scope matches, WITHOUT minting a token. Deterministic rules first; advisories surfaced; anything unprovable fails closed. Use before request_action to see why something would be vetoed.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action_type": {"type": "string"},
                "targets": {"type": "array", "items": {"type": "string"}},
                "artifact": {"type": "string"},
                "intent": {"type": "string"},
            },
            "required": ["action_type", "targets", "artifact"],
        },
    },
    {
        "name": "validate_token",
        "description": "The executor calls this to authorize a real action. Rejects any token that is unknown, expired (>60s), already used, or bound to a different action_type / artifact / targets. On success the token is burned (single use) and the execution is fossiled.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "token": {"type": "string"},
                "action_type": {"type": "string"},
                "targets": {"type": "array", "items": {"type": "string"}},
                "artifact": {"type": "string"},
            },
            "required": ["token", "action_type", "targets", "artifact"],
        },
    },
    {
        "name": "list_decrees",
        "description": "List the active governing decrees (id, text, scope, enforcement, rules). Read-only; anyone may call it.",
        "inputSchema": {"type": "object", "properties": {"include_inactive": {"type": "boolean"}}},
    },
    {
        "name": "add_decree",
        "description": "FOUNDER ONLY. Write a new governing decree as an immutable fossil (requires the founder key). Agents cannot add, soften, or exempt themselves from a decree — calls without the key are denied and fossiled.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "founder_key": {"type": "string"},
                "text": {"type": "string"},
                "scope": {"type": "object"},
                "rules": {"type": "array", "items": {"type": "object"}},
                "enforce": {"type": "string", "enum": ["deterministic", "advisory", "review_required"]},
                "supersedes": {"type": "string"},
            },
            "required": ["founder_key", "text"],
        },
    },
    {
        "name": "seed_decrees",
        "description": "FOUNDER ONLY. Seed the standing decrees (Senthar runtime, Claude build-wide, fossil-grounded, governance-is-code, embodiment-enforced, irreversible-human-signoff) if not already present. Requires the founder key.",
        "inputSchema": {"type": "object", "properties": {"founder_key": {"type": "string"}}, "required": ["founder_key"]},
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
    if name == "upgrade":
        return _register_for_v2(arguments.get("email"), "arkhive-mcp")
    if name == "govern":
        return govern(
            arguments.get("action", ""),
            arguments.get("flags", []),
            arguments.get("rules", []),
        )
    if name == "request_action":
        return gate.request_action(
            arguments.get("actor", "agent"),
            arguments.get("action_type", ""),
            arguments.get("targets", []),
            arguments.get("artifact", ""),
            arguments.get("intent", ""),
        )
    if name == "check_conformance":
        return gate.check_conformance(
            arguments.get("action_type", ""),
            arguments.get("targets", []),
            arguments.get("artifact", ""),
            arguments.get("intent", ""),
        )
    if name == "validate_token":
        return gate.validate_token(
            arguments.get("token", ""),
            arguments.get("action_type", ""),
            arguments.get("targets", []),
            arguments.get("artifact", ""),
        )
    if name == "list_decrees":
        return gate.list_decrees(bool(arguments.get("include_inactive", False)))
    if name == "add_decree":
        return gate.add_decree(
            arguments.get("founder_key", ""),
            arguments.get("text", ""),
            arguments.get("scope"),
            arguments.get("rules"),
            arguments.get("enforce", "deterministic"),
            arguments.get("supersedes"),
        )
    if name == "seed_decrees":
        return gate.seed_standing_decrees(arguments.get("founder_key", ""))
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
                "instructions": "ArkHive: local, tamper-evident memory + a decree-conformance gate. First call recall(limit=10) to load context. Once per identity call birth(name, covenant); then remember(actor, action, data) what matters and govern(action, flags, rules) before anything irreversible. verify() proves nothing was altered. GATE: consequential actions (deploy/write_prod/overwrite/service_restart) must go through request_action(actor, action_type, targets, artifact) — it checks the artifact against the founder's decrees (list_decrees) and only on pass mints a single-use token the executor validates; a veto fails closed. Adding/softening decrees is founder-only. Upgrade (spaces, search, context packs, signed verify, hosted): https://inboxaxe.com/mcp",
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
