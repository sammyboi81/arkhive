# Decree-Conformance Gate — Runbook

Governance as **code, not a prompt**. The founder's decrees become append-only,
hash-chained fossils; consequential actions (deploy / write-prod / restart) can only
happen through a gate that checks the artifact against those decrees and, on pass,
mints a single-use, artifact-bound, 60-second token the executor must present. No pass
→ no token → the action is physically impossible, not merely discouraged.

Everything — decrees, requests, vetoes, token issuance, executions — is one fossil in
the same ArkHive chain, so `verify()` proves the whole record unbroken.

## 0. The one step only the founder can take (the root of trust)

The gate is only sovereign if the **founder key** lives with the founder, never with an
agent. Set it once:

```bash
# option A: environment (per shell / service unit)
export ARKHIVE_FOUNDER_KEY='<a long random secret only you hold>'

# option B: a file only you can read
mkdir -p ~/.arkhive && printf '%s' '<secret>' > ~/.arkhive/founder.key && chmod 600 ~/.arkhive/founder.key
```

Without it, `add_decree` / `seed_decrees` / `deactivate_decree` **fail closed** — you
cannot bootstrap governance from nothing, and an agent that never had the key can never
add, soften, or exempt itself from a decree.

## 1. Founder: seed the standing decrees (once)

```
seed_decrees(founder_key="<secret>")
```

Seeds: `senthar-runtime`, `claude-build-wide`, `fossil-grounded`, `governance-is-code`
(advisory), `irreversible-human-signoff` (review-required), `embodiment-enforced`.
Inspect anytime (no key needed): `list_decrees()`.

## 2. Founder: add or supersede a decree

```
add_decree(
  founder_key="<secret>",
  text="RI runtimes are built in Senthar; the genome is the executing runtime.",
  scope={"action_types":["deploy","overwrite"], "path_globs":["/opt/mario/**"]},
  rules=[{"type":"forbid_ext_on_path","exts":[".py"],
          "path_globs":["/opt/mario/**"],"unless_contains":[".senb"],
          "reason":"a raw .py brain violates Senthar unless it loads the genome"}],
  enforce="deterministic")
```

Decrees are immutable. To retire one, `deactivate_decree(founder_key, decree_id)` writes
a superseding fossil — the old one is never deleted; the chain stays whole.

**Enforcement tiers:**
- `deterministic` — carries machine rules; a firing rule **vetoes** (fail closed).
- `advisory` — a standing principle with no per-artifact test; **surfaced, not blocking**.
- `review_required` — matched but unprovable/irreversible; **blocks pending a human**.

**Rule types** (deterministic):
- `forbid_ext_on_path {exts, path_globs, unless_contains}` — veto a file extension on a
  path unless the artifact proves conformance by containing the required markers.
- `forbid_pattern {pattern, path_globs}` — veto if the regex appears in the artifact.
- `require_pattern {pattern, applies_if_contains, path_globs}` — if the trigger context
  is present but the required pattern is missing, **fail closed**.

## 3. Agent: request an action (the only door)

An agent no longer deploys directly. It calls:

```
request_action(
  actor="agent",
  action_type="deploy",
  targets=["/opt/mario/mario_service.py"],
  artifact="<the actual file contents / diff / plan>",
  intent="ship the grounded claude-first brain")
```

- **Veto** → `{allowed:false, veto_reason, cited_decrees, token:null}`. Fossiled. Stop.
- **Pass** → `{allowed:true, token:"<raw>", expires_in_seconds:60}`. Fossiled.

Dry-run without minting a token: `check_conformance(action_type, targets, artifact)`.

## 4. Executor: validate the token (or refuse)

The real deploy path must call this and refuse any action lacking a valid token:

```
validate_token(token="<raw>", action_type="deploy",
               targets=["/opt/mario/mario_service.py"], artifact="<same bytes>")
```

Rejects unknown / expired / reused / retargeted / mismatched-artifact tokens. On success
the token is **burned** (single use) and `action.EXECUTED` is fossiled. Then, and only
then, does the executor perform the action.

**The capability move (what makes it non-routable):** the gate is the mechanism, but it
only *bites* once the direct deploy path is removed and the executor is wired to require
`validate_token`. That wiring — and revoking the agent's own SSH/write access to prod —
is a **founder action**; an agent cannot remove its own hands (if it could, it could
restore them). Until that is done, the gate is enforcement an honest agent routes
through; after it, bypass is impossible.

## 5. Verify the whole record

```
verify()   # recomputes every hash: decrees, requests, vetoes, tokens, executions
```

`INTACT` proves no decree was altered and no request/veto/execution was forged or
removed. Run it after any dispute.

## How a veto reads

```
{ "allowed": false, "verdict": "VETOED",
  "veto_reason": "[senthar-runtime] a raw .py brain violates Senthar unless it loads the genome",
  "cited_decrees": [{"decree_id":"senthar-runtime","text":"...","enforce":"deterministic"}],
  "vetoes": [{"decree_id":"senthar-runtime","rule":"forbid_ext_on_path","detail":"..."}],
  "token": null, "fossil_idx": 42 }
```

The decree is named, the rule is named, the offending artifact is hashed and fossiled,
and no token exists — so the action cannot proceed.
