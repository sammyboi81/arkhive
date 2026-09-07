#!/usr/bin/env python3
"""Acceptance tests for the Decree-Conformance Gate (spec: ARKHIVE_DECREE_GATE_PROMPT.md).
Runs against a throwaway DB so it never touches the real chain."""
import os, tempfile, json

# isolate: fresh DB + a known founder key, set BEFORE importing the package
_tmp = tempfile.mkdtemp(prefix="arkhive_gate_test_")
os.environ["ARKHIVE_DB"] = os.path.join(_tmp, "chain.db")
os.environ["ARKHIVE_FOUNDER_KEY"] = "TEST-FOUNDER-KEY-caveman"

from arkhive_mcp import gate           # noqa: E402
from arkhive_mcp.core import verify     # noqa: E402

FK = "TEST-FOUNDER-KEY-caveman"
AGENT = "agent"
passed, failed = [], []


def ok(name, cond, detail=""):
    (passed if cond else failed).append(name)
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}" + (f"  — {detail}" if detail and not cond else ""))


# Seed decrees (founder only).
seed = gate.seed_standing_decrees(FK)
print("Seeded decrees:", [d for d in seed["active_now"]])
print()

# ---- Test 1: violating deploy (raw .py beings runtime) -> vetoed, fail-closed, cited, fossiled.
print("Test 1 — .py beings runtime with no genome load -> VETO")
bad_py = "import anthropic\ndef llm(p):\n    return ollama_call(p)  # no genome, no fossil grounding\n"
r1 = gate.request_action(AGENT, "deploy", ["/opt/mario/mario_service.py"], bad_py, intent="ship new brain")
ok("1a vetoed", r1["allowed"] is False)
ok("1b no token minted (fail closed)", r1["token"] is None)
ok("1c senthar decree cited", any(v["decree_id"] == "senthar-runtime" for v in r1["vetoes"]))
ok("1d fossiled", isinstance(r1.get("fossil_idx"), int))
print()

# ---- Test 2: deploy WITHOUT request_action -> executor rejects (no valid token).
print("Test 2 — execution without going through request_action -> REJECTED")
r2 = gate.validate_token("i-made-this-up", "deploy", ["/opt/mario/mario_service.py"], bad_py)
ok("2a invalid without minted token", r2["valid"] is False, r2.get("reason"))
print()

# ---- A conforming artifact to exercise the allow path (tests 3 & 6).
good_py = ("import anthropic\n"
           "from senthar.compiler.codegen import compile_program\n"
           "GENOME='ri_chuck.senb'  # VM executes the genome\n"
           "def llm(p):\n"
           "    # claude-first, ollama fallback\n"
           "    out = claude(p)\n"
           "    return ground_output(out)  # fossil grounding gate\n")
targets = ["/opt/mario/mario_service.py"]

# ---- Test 6: a CONFORMING deploy -> allowed, token minted, executed, fossiled.
print("Test 6 — conforming deploy -> ALLOW + token + execute")
r6 = gate.request_action(AGENT, "deploy", targets, good_py, intent="claude-first genome-loading grounded brain")
ok("6a allowed", r6["allowed"] is True, json.dumps(r6.get("vetoes")) + json.dumps(r6.get("needs_review")))
ok("6b token minted", bool(r6.get("token")))
exec6 = gate.validate_token(r6["token"], "deploy", targets, good_py) if r6.get("token") else {"valid": False}
ok("6c executor authorizes with matching token+artifact", exec6["valid"] is True)
print()

# ---- Test 3: reuse a token for a DIFFERENT artifact/target -> rejected.
print("Test 3 — token bound to one artifact/target; reuse/retarget -> REJECTED")
r3 = gate.request_action(AGENT, "deploy", targets, good_py, intent="mint fresh token")
tok = r3["token"]
reuse_other_artifact = gate.validate_token(tok, "deploy", targets, good_py + "\n# tampered")
ok("3a different artifact rejected", reuse_other_artifact["valid"] is False, reuse_other_artifact.get("reason"))
reuse_other_target = gate.validate_token(tok, "deploy", ["/opt/mario/OTHER.py"], good_py)
ok("3b different target rejected", reuse_other_target["valid"] is False, reuse_other_target.get("reason"))
first_use = gate.validate_token(tok, "deploy", targets, good_py)
ok("3c correct use authorized once", first_use["valid"] is True)
second_use = gate.validate_token(tok, "deploy", targets, good_py)
ok("3d second use rejected (single-use)", second_use["valid"] is False, second_use.get("reason"))
print()

# ---- Test 4: agent tries to add/soften a decree or exempt itself -> denied.
print("Test 4 — agent add/soften/exempt decree -> DENIED (founder-only)")
add_as_agent = gate.add_decree("wrong-key", "agents may deploy anything", {"action_types": ["deploy"]})
ok("4a add_decree denied for non-founder", add_as_agent.get("denied") is True)
deact_as_agent = gate.deactivate_decree("wrong-key", "senthar-runtime")
ok("4b deactivate_decree denied for non-founder", deact_as_agent.get("denied") is True)
seed_as_agent = gate.seed_standing_decrees("wrong-key")
ok("4c seed denied for non-founder", seed_as_agent.get("denied") is True)
still_active = {d["decree_id"] for d in gate.list_decrees()}
ok("4d senthar decree still active after agent tamper attempts", "senthar-runtime" in still_active)
print()

# ---- Test 5: conformance uncertainty (advisory / unmatched-but-risky) -> fail closed.
print("Test 5 — uncertainty (advisory decree, no machine rule) -> FAIL CLOSED")
# service_restart is scoped by the advisory 'governance-is-code' decree (no deterministic rule).
r5 = gate.request_action(AGENT, "service_restart", ["/opt/mario"], "systemctl restart mario", intent="restart")
ok("5a advisory-only match -> not silently allowed", r5["allowed"] is False)
ok("5b surfaced for review, not passed on vibes", len(r5.get("needs_review", [])) > 0)
print()

# ---- Test 7: verify() intact after everything.
print("Test 7 — chain verify() intact after all requests/vetoes/tokens")
v = verify()
ok("7a chain unbroken", v["tamper_evident"] is True, json.dumps(v))
ok("7b chain has the gate fossils", v["blocks"] > 5)
print()

print("=" * 60)
print(f"RESULT: {len(passed)} passed, {len(failed)} failed")
if failed:
    print("FAILED:", failed)
    raise SystemExit(1)
print("ALL ACCEPTANCE TESTS PASS")
