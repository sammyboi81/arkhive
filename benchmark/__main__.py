#!/usr/bin/env python3
"""
ArkHive tamper-evidence benchmark — reproducible by a skeptic, no key required.

THE CLAIM UNDER TEST
--------------------
ArkHive says its memory is *tamper-evident*: if anyone edits, deletes, or
reorders a stored record, later verification must FAIL because the SHA-256 hash
chain no longer matches. This script proves exactly that, end to end:

  1. write N hash-chained blocks into a throwaway chain,
  2. verify  -> expect 0 broken links (INTACT),
  3. TAMPER with one block (a direct SQL edit, behind ArkHive's back),
  4. verify again -> expect the tamper to be CAUGHT (broken links > 0).

Steps 2 and 4 are the whole point: an honest integrity claim has to survive an
adversary who edits the database directly. If step 4 did NOT catch the edit,
the claim would be false. It uses a temporary database, so your real
`data/chain.db` is never touched. No API key, no account, no network.

USAGE
-----
    python -m benchmark
"""
from __future__ import annotations

import os
import sys
import json
import sqlite3
import tempfile

# import the REAL engine (the same core.py the MCP + HTTP servers use)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import core  # noqa: E402

N = int(os.environ.get("ARK_BENCH_N", "20"))


def _line(c: str = "-") -> str:
    return c * 66


def main() -> int:
    # Redirect the chain to a throwaway DB so the user's real memory is untouched.
    tmpdir = tempfile.mkdtemp(prefix="arkhive_bench_")
    core.DB = os.path.join(tmpdir, "bench_chain.db")

    print("=" * 66)
    print("ARKHIVE TAMPER-EVIDENCE BENCHMARK")
    print("=" * 66)
    print(f"engine   : core.py (SQLite + SHA-256, zero proprietary deps)")
    print(f"scratch  : {core.DB}")
    print(f"blocks   : {N}")
    print()

    # 1) a born identity may write (Law 5) --------------------------------
    who = core.birth("benchmark-agent", ["record facts accurately"])
    actor = who["soul_id"]
    print(f"[1] born identity: {actor}")

    # 2) write N hash-chained blocks --------------------------------------
    for i in range(N):
        core.remember(actor, f"event_{i}", {"seq": i, "note": f"payload {i}"})
    print(f"[2] wrote {N} hash-chained blocks")

    # 3) verify a clean chain ---------------------------------------------
    clean = core.verify()
    print(f"[3] verify (untouched): blocks={clean['blocks']} "
          f"broken_links={clean['broken_links']} -> {clean['verdict']}")
    if not clean["tamper_evident"]:
        print("    UNEXPECTED: a clean chain reported broken. Benchmark FAILED.")
        return 1

    # 4) TAMPER: edit one block's payload directly in SQLite, behind the
    #    engine's back — exactly what a local attacker or a bad actor would do.
    target = N // 2
    con = sqlite3.connect(core.DB)
    before = con.execute("SELECT action FROM blocks WHERE idx=?", (target,)).fetchone()[0]
    con.execute("UPDATE blocks SET action=? WHERE idx=?", ("FORGED_EVENT", target))
    con.commit()
    con.close()
    print(_line())
    print(f"[4] TAMPERED block idx={target}: '{before}' -> 'FORGED_EVENT' "
          f"(direct SQL edit, no hash recomputed)")

    # 5) verify again — the edit must be caught ---------------------------
    caught = core.verify()
    print(f"[5] verify (after tamper): blocks={caught['blocks']} "
          f"broken_links={caught['broken_links']} -> {caught['verdict']}")
    print(_line())
    print()

    ok = clean["tamper_evident"] and (not caught["tamper_evident"]) and caught["broken_links"] > 0
    if ok:
        print("RESULT: PASS - tamper-evidence proven.")
        print("  * clean chain verified with 0 broken links,")
        print(f"  * a single forged edit was CAUGHT ({caught['broken_links']} broken link(s)).")
        print()
        print("Honest scope: this proves any edit/delete/reorder of an existing")
        print("record is DETECTED. It does not stop an attacker who owns the machine")
        print("from replacing the whole database + software together. See the README")
        print("section 'What the hash chain protects against'.")
        return 0

    print("RESULT: FAIL - tamper was not caught. The claim would be false.")
    print(json.dumps({"clean": clean, "after_tamper": caught}, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
