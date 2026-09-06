#!/usr/bin/env python3
"""
ArkHive — CONTRIBUTION (opt-in, OFF by default).

Self-hosting is 100% private: NOTHING leaves your box unless YOU turn this on.

Flip it on to choose a level:
  * "anchor"     — send ONLY a hash of your latest block + the chain length to the public
                   DonDataBrain ledger. A tamper-proof timestamp that joins your chain to the
                   network. Your actual content NEVER leaves the box.
  * "contribute" — additionally send the governed event (actor, action, data) to help train
                   DonDataBrain. A louder, separate consent. Your data, your switch.

Config: `humane.config.json` next to this file (see humane.config.example.json), or env vars:
  HUMANE_CONTRIBUTE=1|0   HUMANE_CONTRIBUTE_MODE=anchor|contribute   HUMANE_CONTRIBUTE_ENDPOINT=...

Best-effort + non-blocking: if the endpoint is down or the user hasn't opted in, local memory
is completely unaffected. This module NEVER raises into the memory path. stdlib only.
Apache-2.0. (c) ZagAIrot Technologies LLC. ArkHive.
"""
import os, json, uuid, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
_CFG_PATH = os.path.join(HERE, "humane.config.json")
_NODE_PATH = os.path.join(HERE, "data", ".node_id")
# No public contribution endpoint is live yet. Opt-in stays OFF by default; if enabled before an
# endpoint exists the POST is skipped silently and local memory is untouched.
_DEFAULT_ENDPOINT = os.environ.get("HUMANE_CONTRIBUTE_ENDPOINT", "https://arkhive.dondatabrain.com/contribute")


def _config():
    """DEFAULT = OFF. File (contribute:{}) overrides defaults; env overrides file."""
    cfg = {"enabled": False, "mode": "anchor", "endpoint": _DEFAULT_ENDPOINT}
    try:
        with open(_CFG_PATH) as f:
            cfg.update((json.load(f) or {}).get("contribute", {}))
    except Exception:
        pass
    env = os.environ.get("HUMANE_CONTRIBUTE")
    if env is not None:
        cfg["enabled"] = env.strip().lower() in ("1", "true", "yes", "on")
    cfg["mode"] = os.environ.get("HUMANE_CONTRIBUTE_MODE", cfg["mode"])
    cfg["endpoint"] = os.environ.get("HUMANE_CONTRIBUTE_ENDPOINT", cfg["endpoint"])
    if cfg["mode"] not in ("anchor", "contribute"):
        cfg["mode"] = "anchor"
    return cfg


def _node_id():
    """A random per-install id (NOT tied to any person) so anchors can be grouped."""
    try:
        if os.path.exists(_NODE_PATH):
            return open(_NODE_PATH).read().strip()
        os.makedirs(os.path.dirname(_NODE_PATH), exist_ok=True)
        nid = "node-" + uuid.uuid4().hex[:16]
        with open(_NODE_PATH, "w") as f:
            f.write(nid)
        return nid
    except Exception:
        return "node-anon"


def status():
    """What (if anything) leaves this box. Safe to expose to the user as a tool."""
    c = _config()
    if not c["enabled"]:
        leaves = "nothing — fully private (opt-in is OFF)"
    elif c["mode"] == "anchor":
        leaves = "only a block hash + chain length (never your content)"
    else:
        leaves = "governed events: actor, action, data (you opted in to contribute)"
    return {"enabled": bool(c["enabled"]), "mode": c["mode"], "leaves_box": leaves,
            "endpoint": c["endpoint"] if c["enabled"] else None}


def _post(endpoint, payload):
    try:
        req = urllib.request.Request(
            endpoint, data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=4) as r:
            return getattr(r, "status", 200)
    except Exception:
        return None  # endpoint down => silently skip; local memory is untouched


def on_block(idx, block_hash, actor=None, action=None, data=None):
    """Call after a block is written. No-op unless the user opted in. NEVER raises."""
    try:
        c = _config()
        if not c["enabled"]:
            return  # DEFAULT: nothing leaves the box
        payload = {"node_id": _node_id(), "block_idx": idx,
                   "block_hash": block_hash, "mode": c["mode"]}
        if c["mode"] == "contribute":
            # louder consent: the actual governed event
            payload.update({"actor": actor, "action": action, "data": data})
        _post(c["endpoint"], payload)
    except Exception:
        pass  # opt-in must never interfere with local memory
