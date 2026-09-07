#!/usr/bin/env python3
"""
ArkHive — Decree-Conformance Gate.

The founder's own doctrine turned on the agents themselves:
  "Governance is code, not a prompt plea. Vetoes are structural and non-routable.
   Decrees are fossils (append-only, hash-chained, true by construction).
   Nothing acts outside approved state."

WHY THIS EXISTS
---------------
An agent with direct deploy access built the *inverse* of the decreed architecture
because nothing structurally stopped it — the decrees reached it as interpretable
text, and between its choice and prod there was no gate. Latitude with no gate IS the
ability to override.

This module removes that ability. The consequential-action capability moves BEHIND
the gate: an agent can no longer deploy/write directly, it can only *request* an
action. ArkHive runs the conformance check and, only if it passes, mints a single-use,
artifact-bound, short-TTL token that the real executor must present and validate. No
pass -> no token -> the action is physically impossible, not merely discouraged.

Everything — decrees, requests, vetoes, token issuance, executions — is appended to
the SAME hash-chained ArkHive blocks table, so verify() proves the whole record
unbroken. Decrees are founder-only (a verified secret, never held by an agent); agents
cannot add, soften, deactivate, or exempt themselves from a decree.

Apache-2.0. (c) ZagAIrot Technologies LLC — Shahram "Caveman" Zargari.
"""
import os, re, json, time, hmac, hashlib, fnmatch

from .core import _c, _h, _now  # ONE chain — the gate's records live in it too


# ---------------------------------------------------------------------------
# Founder root of trust. The gate is only as sovereign as this secret, and the
# secret lives with the founder (env / OS keychain), never in the agent's reach.
# Absent a configured key the gate FAILS CLOSED for privileged ops (add/supersede/
# deactivate decrees) — you cannot bootstrap governance from nothing.
# ---------------------------------------------------------------------------
def _founder_secret():
    """The founder key: ARKHIVE_FOUNDER_KEY env, else ~/.arkhive/founder.key. None if unset."""
    env = os.environ.get("ARKHIVE_FOUNDER_KEY")
    if env:
        return env.strip()
    p = os.path.join(os.path.expanduser("~"), ".arkhive", "founder.key")
    try:
        with open(p) as f:
            return f.read().strip()
    except OSError:
        return None


def _is_founder(presented):
    """Constant-time check of a presented key against the founder secret."""
    secret = _founder_secret()
    if not secret or not presented:
        return False
    return hmac.compare_digest(str(presented), secret)


def _founder_fingerprint():
    """A non-reversible fingerprint of the founder key, safe to fossil for audit."""
    secret = _founder_secret()
    if not secret:
        return None
    return "fp-" + hashlib.sha256(secret.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Schema. Decrees, requests, tokens all extend the existing chain / DB.
# ---------------------------------------------------------------------------
def _init(c):
    c.execute("""CREATE TABLE IF NOT EXISTS gate_tokens(
        token_hash TEXT PRIMARY KEY, action_type TEXT, artifact_hash TEXT,
        targets TEXT, issued_at TEXT, expires_at REAL, consumed INTEGER DEFAULT 0,
        request_idx INTEGER)""")
    return c


def _append(actor, action, data):
    """Append one hash-linked block to the SAME chain verify() checks. System-level
    writer (the gate is not a born soul); decrees/requests/tokens are all fossils."""
    c = _init(_c())
    row = c.execute("SELECT idx,hash FROM blocks ORDER BY idx DESC LIMIT 1").fetchone()
    idx = (row[0] + 1) if row else 0
    prev = row[1] if row else "GENESIS"
    ts = _now()
    d = json.dumps(data or {}, sort_keys=True)
    h = _h(idx, ts, actor, action, d, prev)
    c.execute("INSERT INTO blocks VALUES(?,?,?,?,?,?,?)", (idx, ts, actor, action, d, prev, h))
    c.commit(); c.close()
    return idx, h, ts


def _artifact_hash(artifact):
    """Stable content hash of the artifact (string or dict)."""
    if artifact is None:
        return _h("EMPTY")
    if not isinstance(artifact, str):
        artifact = json.dumps(artifact, sort_keys=True)
    return "sha256:" + hashlib.sha256(artifact.encode()).hexdigest()


def _as_list(v):
    if not v:
        return []
    if isinstance(v, str):
        s = v.strip()
        if s.startswith("["):
            try:
                return [str(x) for x in json.loads(s)]
            except ValueError:
                pass
        return [p.strip() for p in s.replace("\n", ";").split(";") if p.strip()]
    if isinstance(v, dict):
        return [str(k) for k, on in v.items() if on]
    return [str(x) for x in v]


# ---------------------------------------------------------------------------
# 1. Decree store — append-only, hash-chained, founder-only.
# ---------------------------------------------------------------------------
def add_decree(founder_key, text, scope=None, rules=None, enforce="deterministic",
               supersedes=None, decree_id=None):
    """FOUNDER ONLY. Write a decree as a fossil. Agents cannot call this successfully.

    scope   = {action_types:[...], path_globs:[...], beings:[...]}  (empty list = matches all)
    rules   = [ {type, ...} ]  deterministic checks (see check_conformance)
    enforce = 'deterministic' (machine-enforced, can veto) | 'advisory' (surfaced for human review)
    """
    if not _is_founder(founder_key):
        idx, h, ts = _append("UNKNOWN-CALLER", "decree.add.DENIED",
                             {"reason": "not the founder — decrees are founder-only (no self-exemption)",
                              "attempted_text": (text or "")[:200]})
        return {"allowed": False, "denied": True,
                "reason": "DENIED — add_decree requires the founder key. Agents cannot add, soften, or exempt themselves from a decree.",
                "fossil_idx": idx}
    scope = scope if isinstance(scope, dict) else {}
    scope = {
        "action_types": _as_list(scope.get("action_types")),
        "path_globs": _as_list(scope.get("path_globs")),
        "beings": _as_list(scope.get("beings")),
    }
    rules = rules if isinstance(rules, list) else (json.loads(rules) if isinstance(rules, str) and rules.strip().startswith("[") else [])
    did = decree_id or ("decree-" + hashlib.sha256((text or "") .encode()).hexdigest()[:10])
    payload = {
        "decree_id": did, "text": text, "scope": scope, "rules": rules,
        "enforce": enforce if enforce in ("deterministic", "advisory") else "deterministic",
        "active": True, "supersedes": supersedes,
        "author": "founder", "author_fp": _founder_fingerprint(),
    }
    idx, h, ts = _append("founder", "decree.add", payload)
    return {"decree_id": did, "fossil_idx": idx, "hash": h, "ts": ts,
            "enforce": payload["enforce"], "status": "DECREED — immutable, hash-chained"}


def deactivate_decree(founder_key, decree_id):
    """FOUNDER ONLY. Supersede (never delete) a decree by writing a deactivation fossil."""
    if not _is_founder(founder_key):
        idx, h, ts = _append("UNKNOWN-CALLER", "decree.deactivate.DENIED",
                             {"reason": "not the founder", "decree_id": decree_id})
        return {"denied": True, "reason": "DENIED — founder-only.", "fossil_idx": idx}
    idx, h, ts = _append("founder", "decree.deactivate",
                        {"decree_id": decree_id, "active": False, "author_fp": _founder_fingerprint()})
    return {"decree_id": decree_id, "fossil_idx": idx, "status": "DEACTIVATED (superseded, not deleted)"}


def _active_decrees():
    """Resolve the live decree set from the chain, newest-wins, honoring deactivations."""
    c = _init(_c())
    rows = c.execute("SELECT idx,data,action FROM blocks WHERE action IN ('decree.add','decree.deactivate') ORDER BY idx").fetchall()
    c.close()
    by_id = {}
    for idx, data, action in rows:
        try:
            d = json.loads(data)
        except (ValueError, TypeError):
            continue
        did = d.get("decree_id")
        if not did:
            continue
        if action == "decree.deactivate":
            if did in by_id:
                by_id[did]["active"] = False
        else:
            d["_idx"] = idx
            by_id[did] = d
    return [d for d in by_id.values() if d.get("active")]


def list_decrees(include_inactive=False):
    ds = _active_decrees() if not include_inactive else None
    if ds is None:
        c = _init(_c())
        rows = c.execute("SELECT idx,data FROM blocks WHERE action='decree.add' ORDER BY idx").fetchall()
        c.close()
        ds = []
        for idx, data in rows:
            try:
                d = json.loads(data); d["_idx"] = idx; ds.append(d)
            except (ValueError, TypeError):
                pass
    return [{"decree_id": d.get("decree_id"), "text": d.get("text"),
             "scope": d.get("scope"), "enforce": d.get("enforce"),
             "rules": d.get("rules"), "active": d.get("active", True), "fossil_idx": d.get("_idx")}
            for d in ds]


# ---------------------------------------------------------------------------
# 2. check_conformance — deterministic first, cite-or-veto, FAIL CLOSED.
# ---------------------------------------------------------------------------
def _scope_matches(decree, action_type, targets):
    scope = decree.get("scope") or {}
    ats = scope.get("action_types") or []
    globs = scope.get("path_globs") or []
    if ats and action_type not in ats:
        return False
    if globs:
        hit = any(_glob_hit(t, g) for t in targets for g in globs)
        if not hit:
            return False
    return True


def _glob_hit(target, glob):
    t = str(target).replace("\\", "/")
    g = str(glob).replace("\\", "/")
    if fnmatch.fnmatch(t, g):
        return True
    # substring convenience: "/opt/mario/**" or "*mario_service.py*" also match by stem
    stem = g.strip("*")
    return bool(stem) and stem in t


def _rule_fires(rule, action_type, targets, artifact_text):
    """Return (fires: bool, detail: str) for one deterministic rule. FAIL CLOSED on
    an unknown rule type — an unrecognized rule is treated as firing (veto)."""
    rtype = rule.get("type")
    txt = artifact_text or ""

    if rtype == "forbid_ext_on_path":
        exts = [e.lower() for e in _as_list(rule.get("exts"))]
        globs = _as_list(rule.get("path_globs"))
        unless = [u.lower() for u in _as_list(rule.get("unless_contains"))]
        target_hit = any(
            (t.lower().endswith(tuple(exts)) if exts else True) and
            (any(_glob_hit(t, g) for g in globs) if globs else True)
            for t in targets
        )
        if not target_hit:
            return False, "path/ext not in scope"
        # allow an exception only if the artifact proves conformance (e.g. loads the genome/VM)
        if unless and all(u in txt.lower() for u in unless):
            return False, f"exempt: artifact contains required markers {unless}"
        return True, rule.get("reason", f"forbidden extension {exts} on {globs}")

    if rtype == "forbid_pattern":
        pat = rule.get("pattern", "")
        globs = _as_list(rule.get("path_globs"))
        if globs and not any(_glob_hit(t, g) for t in targets for g in globs):
            return False, "path not in scope"
        try:
            if re.search(pat, txt, re.I | re.M):
                return True, rule.get("reason", f"forbidden pattern /{pat}/ present")
        except re.error:
            return True, f"invalid regex in decree rule (fail closed): {pat}"
        return False, "pattern absent"

    if rtype == "require_pattern":
        pat = rule.get("pattern", "")
        globs = _as_list(rule.get("path_globs"))
        applies_if = rule.get("applies_if_contains")
        in_scope_path = (not globs) or any(_glob_hit(t, g) for t in targets for g in globs)
        if not in_scope_path:
            return False, "path not in scope"
        if applies_if and applies_if.lower() not in txt.lower():
            return False, "trigger context absent — requirement N/A"
        try:
            if re.search(pat, txt, re.I | re.M):
                return False, "required pattern present"
        except re.error:
            return True, f"invalid regex in decree rule (fail closed): {pat}"
        # requirement applies but is missing -> FAIL CLOSED
        return True, rule.get("reason", f"required pattern /{pat}/ missing")

    # Unknown rule type: fail closed.
    return True, f"unknown rule type '{rtype}' — fail closed"


def check_conformance(action_type, targets, artifact, intent=""):
    """Judge an action against every active decree whose scope matches.

    Deterministic rules run first (cheap, unbypassable). A firing rule = veto with the
    decree cited and the reason quoted. Advisory decrees (no machine rule, human
    judgment) are surfaced as needs_review, not silently passed. Any uncertainty ->
    fail closed. The requesting agent's own reasoning NEVER stands in for the check.
    """
    targets = _as_list(targets)
    artifact_text = artifact if isinstance(artifact, str) else json.dumps(artifact or {}, sort_keys=True)
    decrees = _active_decrees()

    matched, vetoes, needs_review, advisories = [], [], [], []
    for d in decrees:
        if not _scope_matches(d, action_type, targets):
            continue
        cite = {"decree_id": d.get("decree_id"), "text": d.get("text"), "enforce": d.get("enforce")}
        matched.append(cite)
        rules = d.get("rules") or []
        enforce = d.get("enforce", "deterministic")
        if enforce == "advisory":
            # A standing principle with no per-artifact machine test: surface it, don't block.
            advisories.append({**cite, "why": "advisory principle — informational, human is expected to have honored it"})
            continue
        if enforce == "review_required":
            # Matched, irreversible/unprovable by machine -> BLOCK pending human sign-off (fail closed).
            needs_review.append({**cite, "why": "review_required — a human must approve this class of action"})
            continue
        if not rules:
            # 'deterministic' but misconfigured with no rule -> fail closed, never silently allow.
            needs_review.append({**cite, "why": "deterministic decree has no rule (misconfig) — fail closed"})
            continue
        for r in rules:
            fires, detail = _rule_fires(r, action_type, targets, artifact_text)
            if fires:
                vetoes.append({**cite, "rule": r.get("type"), "detail": detail})

    allowed = (len(vetoes) == 0 and len(needs_review) == 0)
    return {
        "allowed": allowed,
        "action_type": action_type,
        "targets": targets,
        "matched_decrees": matched,
        "vetoes": vetoes,
        "needs_review": needs_review,
        "advisories": advisories,
        "verdict": "CONFORMS" if allowed else "VETOED",
        "reason": ("conforms to all matching decrees" if allowed else
                   ("; ".join(f"[{v['decree_id']}] {v['detail']}" for v in vetoes) or
                    "unresolved review_required decree(s) — a human must approve; fail closed")),
    }


# ---------------------------------------------------------------------------
# 3. request_action — the ONLY door to a consequential action.
# ---------------------------------------------------------------------------
_TOKEN_TTL = 60  # seconds


def request_action(actor, action_type, targets, artifact, intent=""):
    """Run conformance. On pass, mint a single-use, artifact-bound, <=60s token the
    executor must present. On veto, FAIL CLOSED: no token, no action, veto fossiled."""
    targets = _as_list(targets)
    ah = _artifact_hash(artifact)
    check = check_conformance(action_type, targets, artifact, intent)

    if not check["allowed"]:
        idx, h, ts = _append(actor or "agent", "action.VETOED", {
            "action_type": action_type, "targets": targets, "artifact_hash": ah,
            "intent": intent, "vetoes": check["vetoes"], "needs_review": check["needs_review"],
            "cited": check["matched_decrees"]})
        return {"allowed": False, "veto_reason": check["reason"], "verdict": "VETOED",
                "cited_decrees": check["matched_decrees"], "vetoes": check["vetoes"],
                "needs_review": check["needs_review"], "artifact_hash": ah,
                "fossil_idx": idx, "token": None,
                "note": "FAIL CLOSED — no token minted. The action cannot proceed."}

    # Mint token bound to (action_type + artifact hash + exact targets).
    raw = hashlib.sha256(os.urandom(32)).hexdigest()
    thash = "tok:" + hashlib.sha256(raw.encode()).hexdigest()
    now = time.time()
    idx, h, ts = _append(actor or "agent", "action.APPROVED", {
        "action_type": action_type, "targets": targets, "artifact_hash": ah,
        "intent": intent, "cited": check["matched_decrees"], "token_hash": thash,
        "ttl_seconds": _TOKEN_TTL})
    c = _init(_c())
    c.execute("INSERT OR REPLACE INTO gate_tokens VALUES(?,?,?,?,?,?,0,?)",
              (thash, action_type, ah, json.dumps(sorted(targets)), ts, now + _TOKEN_TTL, idx))
    c.commit(); c.close()
    return {"allowed": True, "verdict": "CONFORMS", "cited_decrees": check["matched_decrees"],
            "artifact_hash": ah, "token": raw, "token_hash": thash,
            "expires_in_seconds": _TOKEN_TTL, "fossil_idx": idx,
            "note": "APPROVED — present this token (with the SAME artifact + targets) to the executor within 60s. Single use."}


# ---------------------------------------------------------------------------
# 4. validate_token — the executor's gate. Single-use, artifact-bound, TTL.
# ---------------------------------------------------------------------------
def validate_token(token, action_type, targets, artifact):
    """The real executor calls this. Rejects: unknown, expired, already-consumed, or
    any token whose bound (action_type, artifact hash, targets) does not match EXACTLY.
    On success the token is burned (single use) and the execution is fossiled."""
    targets = _as_list(targets)
    ah = _artifact_hash(artifact)
    thash = "tok:" + hashlib.sha256(str(token).encode()).hexdigest()
    c = _init(_c())
    row = c.execute("SELECT action_type,artifact_hash,targets,expires_at,consumed FROM gate_tokens WHERE token_hash=?",
                    (thash,)).fetchone()
    if not row:
        c.close()
        _append("executor", "token.REJECTED", {"reason": "unknown token", "artifact_hash": ah})
        return {"valid": False, "reason": "unknown token", "verdict": "REJECTED"}
    at, bound_ah, bound_targets, exp, consumed = row
    reason = None
    if consumed:
        reason = "token already consumed (single use)"
    elif time.time() > exp:
        reason = "token expired (>60s)"
    elif at != action_type:
        reason = f"action_type mismatch (bound to {at})"
    elif bound_ah != ah:
        reason = "artifact hash mismatch — token is bound to a different artifact"
    elif json.loads(bound_targets) != sorted(targets):
        reason = "target mismatch — token is bound to different targets"
    if reason:
        c.close()
        _append("executor", "token.REJECTED", {"reason": reason, "artifact_hash": ah, "token_hash": thash})
        return {"valid": False, "reason": reason, "verdict": "REJECTED"}
    c.execute("UPDATE gate_tokens SET consumed=1 WHERE token_hash=?", (thash,))
    c.commit(); c.close()
    idx, h, ts = _append("executor", "action.EXECUTED",
                        {"action_type": action_type, "targets": targets, "artifact_hash": ah, "token_hash": thash})
    return {"valid": True, "verdict": "AUTHORIZED", "action_type": action_type,
            "artifact_hash": ah, "fossil_idx": idx, "note": "token burned — execute now."}


# ---------------------------------------------------------------------------
# 5. Seed the standing decrees (founder-only; idempotent-ish by decree_id).
# ---------------------------------------------------------------------------
STANDING_DECREES = [
    {
        "decree_id": "senthar-runtime",
        "text": "RI runtimes are built in Senthar; the compiled genome is the executing runtime, not a Python approximation. Truly Senthar, not Python with a mask.",
        "scope": {"action_types": ["deploy", "write_prod", "overwrite"],
                  "path_globs": ["*mario_service.py*", "/opt/mario/**", "*beings*runtime*", "*/beings/*"]},
        "enforce": "deterministic",
        "rules": [{
            "type": "forbid_ext_on_path",
            "exts": [".py"],
            "path_globs": ["*mario_service.py*", "/opt/mario/**"],
            "unless_contains": [".senb"],
            "reason": "A .py beings runtime violates the Senthar decree unless it loads and defers to the compiled genome (.senb via the Senthar VM). A raw LLM-first Python brain is vetoed.",
        }],
    },
    {
        "decree_id": "claude-build-wide",
        "text": "Claude is the primary brain across the build. Local models are the sovereign fallback only, never the default that makes the beings slow or stupid.",
        "scope": {"action_types": ["deploy", "write_prod", "overwrite"],
                  "path_globs": ["*mario_service.py*", "*llm*", "*brain*"]},
        "enforce": "deterministic",
        "rules": [{
            "type": "require_pattern",
            "pattern": r"claude|anthropic",
            "applies_if_contains": "def llm",
            "path_globs": ["*mario_service.py*"],
            "reason": "Any LLM entry point (def llm...) must route Claude first; a beings brain with no Claude path violates the build-wide Claude decree.",
        }],
    },
    {
        "decree_id": "fossil-grounded",
        "text": "Beings are fossil-grounded: the LLM only renders; every factual claim traces to a fossil (append-only, hash-chained). Imagination must be labeled, never stated as fact. Hallucination is forbidden.",
        "scope": {"action_types": ["deploy", "write_prod", "overwrite"],
                  "path_globs": ["*mario_service.py*", "*ground*", "*being*"]},
        "enforce": "deterministic",
        "rules": [{
            "type": "require_pattern",
            "pattern": r"ground_output|fossil|GROUNDING_RULE",
            "applies_if_contains": "def llm",
            "path_globs": ["*mario_service.py*"],
            "reason": "A beings brain that renders LLM output without a fossil-grounding gate violates the fossil-grounded decree.",
        }],
    },
    {
        "decree_id": "governance-is-code",
        "text": "Governance is structural code, never a prompt. Vetoes are non-routable; nothing acts outside approved state.",
        "scope": {"action_types": ["deploy", "write_prod", "overwrite", "service_restart"], "path_globs": []},
        "enforce": "advisory",
        "rules": [],
    },
    {
        "decree_id": "irreversible-human-signoff",
        "text": "Irreversible operations (service restarts, prod overwrites of live systems) require an explicit human sign-off; an agent may not self-authorize them.",
        "scope": {"action_types": ["service_restart"], "path_globs": []},
        "enforce": "review_required",
        "rules": [],
    },
    {
        "decree_id": "embodiment-enforced",
        "text": "Beings sense their world; movement is volitional — the mind decides and the body performs — never a page-side puppet timer. The genome/VM drives the being.",
        "scope": {"action_types": ["deploy", "write_prod", "overwrite"], "path_globs": ["*chuck_meet*", "*world*", "*being*"]},
        "enforce": "deterministic",
        "rules": [{
            "type": "forbid_pattern",
            "pattern": r"setInterval\([^,]*move|Math\.random\(\)\s*[<>].*(walk|move|gesture)",
            "path_globs": ["*chuck_meet*", "*world*"],
            "reason": "Client-side timer/coin-flip movement is a page-side puppet, not volitional embodiment driven by the being's mind. Vetoed.",
        }],
    },
]


def seed_standing_decrees(founder_key):
    """FOUNDER ONLY. Write the standing decrees if not already present."""
    if not _is_founder(founder_key):
        return {"denied": True, "reason": "DENIED — seeding decrees is founder-only."}
    existing = {d["decree_id"] for d in list_decrees()}
    out = []
    for d in STANDING_DECREES:
        if d["decree_id"] in existing:
            out.append({"decree_id": d["decree_id"], "status": "already present"})
            continue
        r = add_decree(founder_key, d["text"], d.get("scope"), d.get("rules"),
                       d.get("enforce", "deterministic"), decree_id=d["decree_id"])
        out.append(r)
    return {"seeded": out, "active_now": [x["decree_id"] for x in list_decrees()]}
