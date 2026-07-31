# ArkHive MCP
<!-- mcp-name: io.github.sammyboi81/arkhive -->

Local-first governed memory for AI agents, with persistent identity,
tamper-evident history, verification, and constraint-aware decisions.

ArkHive is an open-source
[Model Context Protocol](https://modelcontextprotocol.io) server for developers
and teams that want Claude, Codex, and other MCP clients to retain accountable
context across sessions without sending memory to a hosted service by default.

## Install in one command

```bash
python -m pip install arkhive
```

The installed MCP command is `arkhive`.

> **Release note:** PyPI currently provides version `0.1.0`. The repository
> contains the prepared `0.1.1` metadata; do not publish or register `0.1.1`
> until that package version has been released to PyPI.

## Connect an MCP client

### Claude Desktop

Add this entry to your Claude Desktop MCP configuration, then restart Claude
Desktop:

```json
{
  "mcpServers": {
    "humane": {
      "command": "arkhive",
      "args": []
    }
  }
}
```

If Claude Desktop cannot find commands installed by `pip`, replace
`arkhive` with the absolute path printed by:

```bash
python -c "import shutil; print(shutil.which('arkhive'))"
```

### Codex

```bash
codex mcp add humane -- arkhive
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

After connecting the server, ask your MCP client to perform these calls in
order:

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

- [Website](https://dondatabrain.com)
- [PyPI](https://pypi.org/project/arkhive/)
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
