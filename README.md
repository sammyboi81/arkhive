# ArkHive MCP
<!-- mcp-name: io.github.sammyboi81/arkhive -->

Local-first governed memory for AI agents, with persistent identity,
tamper-evident history, verification, and constraint-aware decisions.

**Tell your AI: “Check the ArkHive.”**

ArkHive is an open-source
[Model Context Protocol](https://modelcontextprotocol.io) server for developers
and teams that want Claude, Codex, and other MCP clients to retain accountable
context across sessions without sending memory to a hosted service by default.

## What you get

- **Memory that survives the session.** Your AI writes what it did and reads it
  back next time — no blank slate every morning.
- **Tamper-evident history.** Every record is hash-chained (SHA-256). Edit,
  delete, or reorder any past record and verification fails — you get evidence
  of change, not silent rewriting.
- **Local-first, no telemetry.** The chain is a plain SQLite file on your
  machine. Nothing is transmitted unless you explicitly opt in.

### Verify it yourself — one command, no key

Don't take "tamper-evident" on faith. Run the proof:

```bash
git clone https://github.com/sammyboi81/arkhive && cd arkhive
./scripts/verify.sh          # or:  python -m benchmark
```

It writes a throwaway hash-chained ledger, verifies it clean, then **forges one
block with a direct SQL edit** and shows verification catch it. Real output:

```
[3] verify (untouched):    blocks=20 broken_links=0 -> INTACT — context provably unbroken
[4] TAMPERED block idx=10: 'event_10' -> 'FORGED_EVENT' (direct SQL edit, no hash recomputed)
[5] verify (after tamper): blocks=20 broken_links=1 -> TAMPERED — 1 broken links
RESULT: PASS - tamper-evidence proven.
```

A clean chain verifies with **0** broken links; a single forged edit is
**caught**. Your real `data/chain.db` is never touched. For the honest limits of
what a hash chain can and cannot protect, see
[What the hash chain protects against](#what-the-hash-chain-protects-against)
below.

> **New: the Claude Code Seatbelt.** Hooks that make Claude Code (and Cursor) ask before anything irreversible, remember the
> project between sessions on this chain, and refuse to say "done" until the code ran. Engine: `pip install sentarion-mcp`
> then `sentarion seatbelt install`. One-click kit with five policies and three skills: https://inboxaxe.com/mcp#seatbelt

## Install in one command

```bash
python -m pip install arkhive-mcp
```

The MCP command is `arkhive-mcp`.

> **Renamed:** this package was formerly published as `humane-intelligence`
> (still installable, now frozen). ArkHive is the product;
> #HumaneIntelligence is the movement.


## Connect an MCP client

### Claude Desktop

Add this entry to your Claude Desktop MCP configuration, then restart Claude
Desktop:

```json
{
  "mcpServers": {
    "arkhive": {
      "command": "arkhive-mcp",
      "args": []
    }
  }
}
```

If Claude Desktop cannot find commands installed by `pip`, replace
`arkhive-mcp` with the absolute path printed by:

```bash
python -c "import shutil; print(shutil.which('arkhive-mcp'))"
```

### Codex

```bash
codex mcp add arkhive -- arkhive-mcp
```

Confirm it is configured with:

```bash
codex mcp list
```

## Available tools

| Tool | What it does |
| --- | --- |
| `birth` | Creates a stable agent identity with an explicit covenant. |
| `remember` | Appends a hash-linked, tamper-evident record for a born identity. |
| `recall` | Retrieves prior records so an agent can ground the current session. |
| `verify` | Recomputes and checks the local chain for later alteration or broken links. |
| `govern` | Evaluates an action against deterministic constraints and records the verdict. |

The local chain is stored in SQLite. The exact location depends on where the
server command is launched; use a dedicated working directory if you want to
control where its `data/chain.db` file lives.

## Two-minute verification

After connecting the server, say **“Check the ArkHive”**, or ask your MCP
client to perform these calls in order:

1. Call `birth` with the name `verification-agent` and covenant
   `["record facts accurately", "verify before claiming completion"]`.
2. Copy the returned identity and call `remember` with action
   `installation_verified` and data `{"source": "local MCP test"}`.
3. Call `recall` for that identity and confirm the record appears.
4. Call `verify` and confirm the chain reports as valid.
5. Call `govern` for a harmless test action and inspect the recorded verdict.

This exercises identity, persistence, retrieval, integrity verification, and
governance without production data.

## Privacy and optional contribution

Local-only behavior is the default. With contribution disabled, no chain
content or hashes are intentionally sent by ArkHive.

Copy `humane.config.example.json` to `humane.config.json` only if you want to
opt in:

| Mode | What leaves the machine |
| --- | --- |
| Default (`enabled: false`) | Nothing is intentionally transmitted. |
| `anchor` | The latest block hash and chain length. Memory content is not included. |
| `contribute` | The governed event fields described in the example configuration, in addition to anchoring data. |

Anchoring and contribution are optional, best-effort, and off by default.
Review the configured endpoint and event contents before enabling either mode.

## What the hash chain protects against

The chain is **tamper-evident**: editing, deleting, or reordering an existing
record should cause later verification to fail because hashes no longer match.
This provides useful evidence of change and makes accidental or unsophisticated
local alteration detectable.

It does **not** prevent an attacker with full control of the machine from
replacing the database and software together, deleting all history, restoring
an older snapshot, stealing readable local data, or generating a new internally
consistent chain. Independent anchoring can strengthen evidence that a
particular chain state existed at a particular time, but it does not make the
local host immune to compromise.

## Project links


## Beyond self-hosting — the paid tier

The MCP server on this page is free forever (Apache-2.0, self-host, no telemetry).
When you want more than DIY:

- **Hosted ArkHive** — one URL, no install, no key:
  `https://arkhive.dondatabrain.com/mcp` (add it to Claude Code with
  `claude mcp add --transport http arkhive https://arkhive.dondatabrain.com/mcp`).
- **Custom AI agent, built for you** — a working MCP agent wired into your
  Claude or ChatGPT in one call, done-for-you by the founder:
  [$700 flat](https://inboxaxe.com/offer_agent.html).
- **ArkHive Enterprise** — hand-delivered install + pilot on your own server,
  from $2,500: [sam@inboxaxe.com](mailto:sam@inboxaxe.com?subject=ArkHive%20Enterprise%20install).

Built by the team behind [InboxAxe](https://inboxaxe.com) — the governed AI
marketing platform where nothing sends without your yes.

- [Website](https://dondatabrain.com)
- [PyPI](https://pypi.org/project/arkhive-mcp/)
- [Source](https://github.com/sammyboi81/arkhive)
- [Issues](https://github.com/sammyboi81/arkhive/issues)
- [Apache-2.0 license](./LICENSE)

## Contributing

Issues and pull requests are welcome. Please keep local-only operation as the
default, avoid introducing telemetry, and include tests for changes to memory
or governance behavior.

ArkHive is the open governed-memory layer beneath
[DonDataBrain](https://dondatabrain.com). The mission is humane, accountable AI;
the public MCP listing leads with functionality that users can independently
verify.

Apache-2.0 © 2026 ZagAIrot Technologies LLC.
