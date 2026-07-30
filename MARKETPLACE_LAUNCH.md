# Humane Intelligence MCP marketplace launch

Updated: 2026-07-26 UTC

## Public positioning

- **Name:** Humane Intelligence MCP
- **Short description:** Local-first governed memory for AI agents, with
  persistent identity, tamper-evident history, verification, and
  constraint-aware decisions.
- **Search tagline:** Persistent, verifiable memory and governance for Claude,
  Codex, and other MCP clients.
- **Repository:** https://github.com/sammyboi81/humane-intelligence
- **PyPI:** https://pypi.org/project/humane-intelligence/
- **License:** Apache-2.0

## GitHub discovery metadata

- **Description:** Local-first governed memory for AI agents: persistent
  identity, tamper-evident history, verification, and constraint-aware
  decisions.
- **Topics:** `mcp`, `model-context-protocol`, `ai-memory`, `agent-memory`,
  `ai-governance`, `tamper-evident`, `audit-log`, `local-first`,
  `responsible-ai`
- **Social preview:** See `SOCIAL_PREVIEW.md`.

## Version gate

PyPI currently installs `humane-intelligence==0.1.0`. The repository packaging
metadata is `0.1.1`. A clean install of `0.1.0` succeeded, but MCP
initialization hung; do not submit that artifact. The official registry
validator accepts the current `0.1.0` metadata, but publication remains blocked
on the working `0.1.1` PyPI release. Do not create a `0.1.1` registry record or
GitHub release before the matching PyPI artifact is live.

## Registry status

| Registry | Submission URL | Status | Requirement |
| --- | --- | --- | --- |
| Official MCP Registry | https://modelcontextprotocol.io/registry/quickstart | Prepared; not published | GitHub device login, package validation, and acceptance of registry terms |
| Smithery | https://smithery.ai/servers/new | Prepared; not published | Account login and an MCPB bundle for this local stdio server, or a compatible public Streamable HTTP endpoint |
| Glama | https://glama.ai/mcp/servers | Prepared; not submitted | Account/GitHub authorization and repository selection |
| GitHub MCP discovery | Official Registry metadata | Prepared | Becomes discoverable through the official registry after publication |

No hosted telemetry is introduced by these materials.
