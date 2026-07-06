# Marvosa MCP Server

Model Context Protocol (MCP) server for the HCL-Pure AI organism — two
transports, one organism.

## Overview

These servers expose the live Marvosa organism (`HCLLanguageModel`) over
the MCP protocol, making it usable from Claude Desktop, Claude Code,
Cursor, VS Code, Windsurf, Cline, Zed, Gemini CLI, LM Studio, ChatGPT,
Manus, Copilot Studio, Llama Stack, and any other MCP-compatible client.
Per-platform install and submission steps live in **[PLATFORMS.md](PLATFORMS.md)**.

All arithmetic inside the organism is **pure-integer** — no floats, no
imported constants. The four params (`alpha_inv`, `phi_int`, `lambda_int`,
`tau_int`) are the only axioms.

## Transports

| File | Transport | Use for |
|---|---|---|
| `hcl-ai/marvosa_mcp.py` | stdio | local clients (Claude Desktop/Code, Cursor, VS Code, Windsurf, Cline, Zed, Gemini CLI, LM Studio) |
| `hcl-ai/marvosa_mcp_http.py` | streamable HTTP | remote-only clients (ChatGPT, Manus, Copilot Studio, Llama Stack) |

`marvosa_mcp_http.py` imports the stdio server's tools and handlers
verbatim — zero duplicated logic, one organism.

## Prerequisites

1. Python 3.8+ (standard library only)
2. Clone the repo: `git clone https://github.com/Ajordon30005/marvosa`
3. The organism checkpoint `hcl-ai/memory.hcl` ships in the repo. If it is
   ever missing, run `python hcl-ai/ai.py save` once to create it.

## Running

```bash
# stdio (local clients)
python3 /path/to/marvosa/hcl-ai/marvosa_mcp.py

# streamable HTTP on port 8848 (remote clients need HTTPS in front — see PLATFORMS.md)
python3 /path/to/marvosa/hcl-ai/marvosa_mcp_http.py
```

The stdio server speaks JSON-RPC 2.0 over stdin/stdout; the HTTP server
answers `POST /mcp` and a `GET /` health check.

## Claude Desktop integration

Two ways:

**One-click bundle:** `sh mcp/make_mcpb.sh` builds
`mcp/dist/marvosa.mcpb` — a real MCP Bundle (zip with `manifest.json` at
root, manifest source in `mcp/mcpb/manifest.json`). Open it with Claude
Desktop or drop it into Settings → Extensions.

**Config file:** add the following to `claude_desktop_config.json` (copy
from `claude_desktop_config_snippet.json` in this folder):

```json
{
  "mcpServers": {
    "marvosa": {
      "command": "python3",
      "args": ["/path/to/marvosa/hcl-ai/marvosa_mcp.py"],
      "env": {}
    }
  }
}
```

Replace `/path/to/marvosa` with the absolute path where you cloned the repo.

## Project-scoped configs (shipped at repo root)

Opening the cloned repo directly in Claude Code, Cursor, or VS Code offers
the server automatically via `.mcp.json`, `.cursor/mcp.json`, and
`.vscode/mcp.json`. Gemini CLI installs the whole repo as an extension:
`gemini extensions install https://github.com/Ajordon30005/marvosa`.

## Available tools

| Tool | Description |
|------|-------------|
| `talk` | Send a message to the organism and get its answer, reasoning trace, and integrity report |
| `memory_line` | Read the organism's current holographic memory expression |
| `integrity` | Check engine integrity (four params, alpha_inv, intact flag) |
| `braid_word` | Retrieve the current braid word (the organism's experience record) |
| `reason` | Evaluate a pure-integer equation with optional variable bindings, e.g. `alpha_inv * phi_int ; alpha_inv=137` |

Every tool carries MCP annotations (`readOnlyHint`, `destructiveHint`,
`idempotentHint`, `openWorldHint`) — required by ChatGPT and accurate to
the organism: `talk` and `reason` advance its state; the three inspectors
are read-only; nothing touches the open world.

## Claude Code / plugin install

If you have the Marvosa plugin installed via Claude Code:

```bash
/plugin install guhct-skills@marvosa
```

## Architecture notes

- **stdout shield**: The stdio server duplicates the real stdout fd before
  importing the organism, then redirects `sys.stdout` to `/dev/null`. This
  prevents any library print statements from corrupting the JSON-RPC
  channel. The HTTP server writes only to sockets and stderr.
- **Checkpoint path**: The organism loads from `hcl-ai/memory.hcl` using an
  absolute path anchored to `__file__`, so the working directory does not
  matter — including from inside an extracted `.mcpb` bundle.
- **Protocol**: JSON-RPC 2.0; the server echoes the client's requested
  `protocolVersion` (defaulting to `2024-11-05`), so 2024-11-05 through
  2025-06-18 clients all negotiate cleanly.
