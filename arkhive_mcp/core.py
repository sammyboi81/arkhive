#!/usr/bin/env python3
"""
ArkHive — core memory + governance logic (transport-agnostic).

The ONE source of truth for the tamper-evident chain. Both transports import this:
  * server.py    — MCP (stdio), for Claude Desktop/Code/Cursor
  * http_app.py  — REST (HTTPS), for ChatGPT Custom GPTs / any web client

SQLite + SHA-256. Zero proprietary dependencies. Apache-2.0.
(c) ZagAIrot Technologies LLC. ArkHive.
"""
import os, json, sqlite3, hashlib, time

HERE = os.path.dirname(os.path.abspath(__file__))
_LEGACY_DB = os.path.join(HERE, "data", "chain.db")


def _db_path():
    """ARKHIVE_DB env wins; a pre-0.2 in-package chain is honored; else ~/.arkhive."""
    env = os.environ.get("ARKHIVE_DB")
    if env:
        return env
    if os.path.exists(_LEGACY_DB):
        return _LEGACY_DB
    return os.path.join(os.path.expanduser("~"), ".arkhive", "chain.db")


DB = _db_path()
_d = os.path.dirname(DB)
if _d:
    os.makedirs(_d, exist_ok=True)


def _c():
    c = sqlite3.connect(DB); c.execute("PRAGMA journal_mode=WAL")
    c.execute("""CREATE TABLE IF NOT EXISTS souls(idx INTEGER PRIMARY KEY, soul_id TEXT UNIQUE,
        name TEXT, covenant TEXT, born_at TEXT, prev_hash TEXT, hash TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS blocks(idx INTEGER PRIMARY KEY, ts TEXT, actor TEXT,
        action TEXT, data TEXT, prev_hash TEXT, hash TEXT)""")
    return c


def _h(*parts): return hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest()
def _now(): return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _as_list(v):
    """Accept list | JSON string | 'a; b' string | {name: true} dict -> list[str]."""
    if not v:
        return []
    if isinstance(v, dict):
        return [str(k) for k, on in v.items() if on]
    if isinstance(v, str):
        s = v.strip()
        if s.startswith("["):
            try:
                return [str(x) for x in json.loads(s)]
            except ValueError:
                pass
        return [p.strip() for p in s.replace("\n", ";").split(";") if p.strip()]
    return [str(x) for x in v]


def _as_rules(v):
    """Accept [{trigger, action}] | {trigger: action} | JSON string -> [{trigger, action}]."""
    if not v:
        return []
    if isinstance(v, str):
        try:
            v = json.loads(v)
        except ValueError:
            return []
    if isinstance(v, dict):
        return [{"trigger": str(k), "action": (str(a.get("action", "refuse")) if isinstance(a, dict) else str(a))}
                for k, a in v.items()]
    return [r if isinstance(r, dict) else {"trigger": str(r), "action": "refuse"} for r in v]


def birth(name, covenant):
    covenant = _as_list(covenant)
    c = _c(); row = c.execute("SELECT idx,hash FROM souls ORDER BY idx DESC LIMIT 1").fetchone()
    idx = (row[0]+1) if row else 0; prev = row[1] if row else "GENESIS"
    seq = c.execute("SELECT COUNT(*)+1 FROM souls WHERE name=?", (name,)).fetchone()[0]
    sid = f"{''.join(ch if ch.isalnum() else '-' for ch in name.lower()).strip('-') or 'ri'}-ri-{seq:03d}"
    ts = _now(); cov = json.dumps(covenant); h = _h(idx, sid, name, cov, ts, prev)
    c.execute("INSERT INTO souls VALUES(?,?,?,?,?,?,?)", (idx, sid, name, cov, ts, prev, h))
    c.commit(); c.close()
    return {"soul_id": sid, "name": name, "covenant": covenant, "born_at": ts, "status": "BORN — identity bound, immutable"}


def is_born(sid):
    if not sid: return False
    c = _c(); r = c.execute("SELECT 1 FROM souls WHERE soul_id=?", (sid,)).fetchone(); c.close(); return r is not None


def resolve_actor(actor):
    """Accept a soul_id or a birth name; return the canonical soul_id, or None."""
    if not actor: return None
    c = _c()
    try:
        if c.execute("SELECT 1 FROM souls WHERE soul_id=?", (actor,)).fetchone():
            return actor
        r = c.execute("SELECT soul_id FROM souls WHERE name=? ORDER BY idx DESC LIMIT 1", (actor,)).fetchone()
        return r[0] if r else None
    finally:
        c.close()


def remember(actor, action, data):
    sid = resolve_actor(actor)
    if not sid:
        return {"refused": True, "reason": f"'{actor}' is not a born soul. Earn identity via birth() first (Law 5), then act as the returned soul_id (or your birth name).", "verdict": "REFUSED"}
    actor = sid
    c = _c(); row = c.execute("SELECT idx,hash FROM blocks ORDER BY idx DESC LIMIT 1").fetchone()
    idx = (row[0]+1) if row else 0; prev = row[1] if row else "GENESIS"; ts = _now()
    d = json.dumps(data or {}); h = _h(idx, ts, actor, action, d, prev)
    c.execute("INSERT INTO blocks VALUES(?,?,?,?,?,?,?)", (idx, ts, actor, action, d, prev, h))
    c.commit(); c.close()
    # OPT-IN contribution (OFF by default; nothing leaves the box unless the user enabled it).
    try:
        from . import contribution
        contribution.on_block(idx, h, actor, action, d)
    except Exception:
        pass  # opt-in must never affect local memory
    return {"idx": idx, "hash": h, "prev_hash": prev, "ts": ts, "note": "immutably recorded"}


def contribution_status():
    """Report exactly what (if anything) leaves the box. Wraps contribution.status()."""
    try:
        from . import contribution
        return contribution.status()
    except Exception:
        return {"enabled": False, "mode": "anchor", "leaves_box": "nothing — fully private"}


def recall(actor=None, limit=10):
    if actor:
        actor = resolve_actor(actor) or actor
    c = _c()
    q = "SELECT idx,ts,actor,action,data FROM blocks" + (" WHERE actor=?" if actor else "") + " ORDER BY idx DESC LIMIT ?"
    rows = c.execute(q, ((actor, limit) if actor else (limit,))).fetchall(); c.close()
    return [{"idx": r[0], "ts": r[1], "actor": r[2], "action": r[3], "data": r[4]} for r in rows]


def verify():
    c = _c(); rows = c.execute("SELECT idx,ts,actor,action,data,prev_hash,hash FROM blocks ORDER BY idx").fetchall(); c.close()
    broken = 0; prev = "GENESIS"
    for r in rows:
        if _h(r[0], r[1], r[2], r[3], r[4], prev) != r[6] or r[5] != prev: broken += 1
        prev = r[6]
    return {"blocks": len(rows), "broken_links": broken, "tamper_evident": broken == 0,
            "verdict": "INTACT — context provably unbroken" if broken == 0 else f"TAMPERED — {broken} broken links"}


def govern(action, flags, rules):
    flags = _as_list(flags); rules = _as_rules(rules)
    for rule in rules:
        if rule.get("trigger") in flags:
            return {"action": action, "vetoed": True, "reason": f"Veto: {rule['trigger']} -> {rule.get('action','blocked')}", "verdict": "VETOED"}
    return {"action": action, "vetoed": False, "reason": "allowed", "verdict": "ALLOWED"}
