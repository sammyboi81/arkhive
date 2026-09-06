"""Smoke test: talks to the installed `arkhive-mcp` server over stdio with a real MCP client.
Run:  python test.py      (uses a throwaway chain via ARKHIVE_DB)"""
import asyncio, os, sys, tempfile
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
os.environ["ARKHIVE_DB"] = os.path.join(tempfile.mkdtemp(), "chain.db")


async def c(s, n, a):
    return (await s.call_tool(n, a)).content[0].text


async def main():
    p = StdioServerParameters(command=sys.executable, args=["-m", "arkhive_mcp.server"], env=dict(os.environ))
    async with stdio_client(p) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize(); print("tools:", [t.name for t in (await s.list_tools()).tools])
            print("\n1 unborn remember -> REFUSED:", await c(s, "remember", {"actor": "nobody", "action": "x"}))
            print("\n2 birth:", await c(s, "birth", {"name": "Ember", "covenant": ["truth over comfort"]}))
            print("\n3 govern(delete, irreversible):", await c(s, "govern", {"action": "delete all", "flags": ["irreversible"], "rules": [{"trigger": "irreversible", "action": "block"}]}))
            print("\n3b govern, legacy dict shapes:", await c(s, "govern", {"action": "x", "flags": {"raw_pii": True}, "rules": {"raw_pii": "refuse"}}))
            print("\n4 born remember -> ALLOWED:", await c(s, "remember", {"actor": "Ember", "action": "context kept forever, freely"}))
            print("\n5 recall:", await c(s, "recall", {"limit": 2}))
            print("\n6 verify:", await c(s, "verify", {}))


asyncio.run(main())
