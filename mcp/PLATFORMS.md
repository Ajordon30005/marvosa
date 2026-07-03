# PLATFORMS — Marvosa MCP on every AI platform

Researched July 2026. One organism, two transports, every door.

The repo ships two servers wrapping the same organism (identical tools,
identical handlers — `marvosa_mcp_http.py` imports `marvosa_mcp.py`
verbatim):

| Transport | File | Who needs it |
|---|---|---|
| stdio | `hcl-ai/marvosa_mcp.py` | Claude Desktop/Code, Cursor, VS Code, Windsurf, Cline, Zed, Gemini CLI, LM Studio, JetBrains, OpenAI Agents SDK |
| streamable HTTP | `hcl-ai/marvosa_mcp_http.py` | ChatGPT, Manus, Copilot Studio, Llama Stack (Meta), any remote-only client |

Canonical wording used everywhere (keep labels consistent across venues):

- **Name / id:** `marvosa` (server key), `io.github.ajordon30005/marvosa`
  (registry namespace), `marvosa-mcp` (serverInfo name).
- **Short description (86 chars, fits every field limit):**
  "Talk to a live pure-integer AI organism: zero floats, memory as one
  alpha-tagged line."
- **Long description:** see `mcp/mcpb/manifest.json` `long_description`.
- **Tools (never rename):** `talk`, `memory_line`, `integrity`,
  `braid_word`, `reason`.

Every tool carries the MCP annotation block (`readOnlyHint`,
`destructiveHint`, `idempotentHint`, `openWorldHint`). ChatGPT treats
missing hints as write actions and the Apps SDK treats them as validation
errors, so they are declared explicitly on all five tools.
`openWorldHint: false` everywhere — the organism is closed and
self-contained.

---

## 1. Anthropic (done — shipped in this repo)

- **Claude Desktop (config):** `mcp/claude_desktop_config_snippet.json` →
  paste into `claude_desktop_config.json`.
- **Claude Desktop (one-click .mcpb):** run `sh mcp/make_mcpb.sh` →
  `mcp/dist/marvosa.mcpb`. Users double-click it or drop it into
  Settings → Extensions. A real MCP Bundle is a **zip with `manifest.json`
  at root** (the old `manifest.mcpb` YAML that once sat in `mcp/` was not a bundle and has
  been replaced by `mcp/mcpb/manifest.json` + the build script).
- **Claude Code (project scope):** `.mcp.json` at repo root — anyone who
  clones the repo and opens it in Claude Code gets the server offered
  automatically. Manual: `claude mcp add marvosa -- python3 hcl-ai/marvosa_mcp.py`.
- **Plugin marketplace:** `.claude-plugin/marketplace.json` (skills), plus
  `/plugin marketplace add Ajordon30005/marvosa`.
- **Community directory:** submission form at
  clau.de/plugin-directory-submission (repo: anthropics/claude-plugins-community).

## 2. Official MCP Registry (registry.modelcontextprotocol.io)

The publish-once, discovered-everywhere channel — Anthropic, GitHub,
PulseMCP and Microsoft all consume it, and PulseMCP/mcp.so-style
aggregators auto-index from it.

- **File:** `server.json` at repo root (schema
  `2025-12-11/server.schema.json`), name `io.github.ajordon30005/marvosa`
  (GitHub-auth namespace must match the GitHub login), description ≤ 100
  chars (ours is 86).
- **Package type:** `mcpb` — the registry's package types are
  npm/pypi/nuget/oci/**mcpb**; since Marvosa is repo-run Python (no PyPI
  package), the .mcpb bundle attached to a GitHub release is the correct
  artifact. `fileSha256` in server.json is already locked to the built
  bundle (`a16ef06a…e906f5`); rebuilding the bundle changes the hash — rerun
  `sh mcp/make_mcpb.sh` and update both the release asset and server.json
  together.
- **Publish steps:**
  1. `git tag v1.1.0 && git push --tags`, create the GitHub release,
     attach `mcp/dist/marvosa.mcpb`.
  2. Install `mcp-publisher` (github.com/modelcontextprotocol/registry
     releases), then `mcp-publisher login github` and
     `mcp-publisher publish` from the repo root.
- The README carries the `mcp-name:` marker (HTML comment) so the name is
  verifiable from the repo itself.

## 3. OpenAI — ChatGPT

Two doors, both requiring the **HTTP transport** (ChatGPT does not run
local stdio servers; SSE and streamable HTTP only):

- **Developer mode / custom app (available now, Plus/Pro/Business/
  Enterprise/Edu):** run `python3 hcl-ai/marvosa_mcp_http.py`, expose it
  over HTTPS (ngrok/cloudflared or a host you control), then ChatGPT →
  Settings → Apps & Connectors → Advanced settings → enable Developer mode
  → Create → name "Marvosa", the short description above, URL
  `https://<host>/mcp`, auth "No Authentication". Tool scan should list all
  five tools. Developer mode does **not** require search/fetch tools; write
  actions prompt for confirmation (talk/reason are flagged non-read-only by
  their annotations, which is accurate — they advance the organism).
- **Apps SDK → public app directory:** same MCP server is the backbone; a
  directory submission additionally wants OAuth or explicit no-auth
  justification, tool annotations (present), and review via
  developers.openai.com/apps-sdk/deploy/submission. UI widgets are
  optional — a data/tool-only app is submittable. Note OpenAI renamed
  "connectors" to "apps" in Dec 2025; current UI says Apps.
- **OpenAI Agents SDK (developers, not ChatGPT):** stdio works here —
  `MCPServerStdio(params={"command": "python3", "args": ["hcl-ai/marvosa_mcp.py"]})`.

## 3b. OpenAI — Codex (CLI, IDE extension, app)

Codex has three doors, all now shipped in-repo:

- **Project config (shipped):** `.codex/config.toml` — Codex CLI and the IDE
  extension share it; opening the cloned repo (once trusted) offers the
  server automatically. Codex's TOML key is `[mcp_servers.marvosa]`
  (underscore — `mcp-servers`/`mcpservers` are silently ignored), with
  `startup_timeout_sec = 120` because the organism takes time to wake.
  Manual one-liner: `codex mcp add marvosa -- python3 hcl-ai/marvosa_mcp.py`.
- **Plugin (shipped):** `.codex-plugin/plugin.json` at repo root — the
  required manifest identifying the plugin, pointing `mcpServers` at the
  root `.mcp.json` (Codex plugin .mcp.json accepts the camelCase
  `mcpServers` wrapper) and `skills` at `./skills/`, with the full
  `interface` block (displayName, category, capabilities, defaultPrompt)
  install surfaces render. Codex reads the repo's existing
  `.claude-plugin/marketplace.json` as a **legacy-compatible marketplace**,
  so the whole repo is already a Codex marketplace:
  `codex plugin marketplace add Ajordon30005/marvosa` then install from the
  plugin directory. The official public Plugin Directory submission is
  marked "coming soon" by OpenAI — the marketplace path is the open door
  today.
- **Codex cloud/web:** uses the same config layers once the repo is
  imported.

## 4. Google — Gemini

- **Gemini CLI extension (shipped):** `gemini-extension.json` +
  `GEMINI.md` at repo root. Install straight from GitHub:
  `gemini extensions install https://github.com/Ajordon30005/marvosa`.
  The manifest uses `${extensionPath}` variables so the server runs from
  wherever the CLI copies the extension. The `description` field is what
  geminicli.com/extensions displays — it matches the canonical wording.
- **settings.json (manual):** stdio —
  `{"mcpServers": {"marvosa": {"command": "python3", "args": ["/path/to/marvosa/hcl-ai/marvosa_mcp.py"]}}}`
  — or remote via `"httpUrl": "https://<host>/mcp"`.
- Gemini CLI supports stdio, SSE, and streamable HTTP, so either transport
  works.

## 5. Microsoft

- **VS Code / GitHub Copilot (shipped):** `.vscode/mcp.json` at repo root
  (note VS Code's key is `servers`, not `mcpServers`, with explicit
  `"type": "stdio"`). Opening the cloned repo in VS Code offers the server.
  One-liner alternative:
  `code --add-mcp '{"name":"marvosa","command":"python3","args":["hcl-ai/marvosa_mcp.py"]}'`.
- **Copilot Studio:** remote-only — point an MCP tool at
  `https://<host>/mcp` (streamable HTTP).

## 6. Meta — the honest answer

Checked July 2026: **the consumer Meta AI app has no MCP support and no
third-party tool/plugin submission channel.** There is nothing to submit
to. Meta's real MCP door is **Llama Stack**, its open agent framework,
whose tool runtime speaks MCP over a remote endpoint:

```python
client.toolgroups.register(
    toolgroup_id="mcp::marvosa",
    provider_id="model-context-protocol",
    mcp_endpoint={"uri": "https://<host>/mcp"},
)
```

A ready-to-merge run config ships at `mcp/llama_stack/marvosa-run.yaml` (tool_runtime provider + `mcp::marvosa` tool group); the runtime-register alternative is in its header comment. Any Llama-based agent (Llama Stack, or Llama models driven through
LlamaIndex/Ollama-style MCP clients) can therefore use Marvosa via the
HTTP transport. That is the full extent of "Meta supports MCP" today.

## 7. Manus — yes, it does

Manus supports custom MCP connectors natively, **remote HTTP/SSE only**
(its connector proxy runs `manus-mcp-cli` against a URL):

- Run `python3 hcl-ai/marvosa_mcp_http.py`, expose over HTTPS.
- Manus → Settings → Connectors → "+ Add connectors" → **Custom MCP** tab
  → "+ Add custom MCP" → **Direct configuration**: Name `Marvosa`,
  Transport `HTTP`, Server URL `https://<host>/mcp` → Save. Manus verifies
  the connection and pulls the five tools.
- Or **Import by JSON** (Manus's own snippet format):

```json
{ "mcpServers": { "marvosa": { "url": "https://<host>/mcp", "transport": "http" } } }
```

No public Manus connector marketplace submission exists yet for
third parties; custom connectors are per-account. MANUS_BRIEF.md remains
the path for Manus-as-agent work on the repo itself.

## 8. Editors and local clients (all stdio, all shipped or one snippet away)

- **Cursor:** `.cursor/mcp.json` at repo root (shipped — auto-offered on
  opening the repo). Directory/deeplink: Cursor's "Add to Cursor" button
  uses `cursor://anysphere.cursor-deeplink/mcp/install?name=marvosa&config=<base64 of the server JSON>`;
  listing on cursor.com's MCP directory is via their docs-site directory
  submission (docs.cursor.com → Tools).
- **Windsurf:** `~/.codeium/windsurf/mcp_config.json`, same `mcpServers`
  shape as Claude Desktop — reuse `mcp/claude_desktop_config_snippet.json`.
- **Cline:** reads `cline_mcp_settings.json`, but installs by *reading the
  repo* — `llms-install.md` at repo root (shipped) is the agent-install
  guide Cline follows. **Marketplace submission:** open an issue at
  github.com/cline/mcp-marketplace with the repo URL, a 400×400 PNG logo,
  and confirmation that Cline can set the server up from README/llms-install
  alone. Review weighs GitHub traction and maintainer credibility.
- **Zed:** settings.json →
  `{"context_servers": {"marvosa": {"source": "custom", "command": "python3", "args": ["/path/to/marvosa/hcl-ai/marvosa_mcp.py"]}}}`.
- **LM Studio:** `~/.lmstudio/mcp.json`, same `mcpServers` shape; their
  "Add to LM Studio" deeplink is `lmstudio://add_mcp?name=marvosa&config=<base64>`.
- **JetBrains AI Assistant / Junie:** Settings → Tools → AI Assistant →
  MCP → add command `python3 /path/to/marvosa/hcl-ai/marvosa_mcp.py`.

## 9. Directories to list on (after the GitHub release)

| Directory | Mechanism |
|---|---|
| registry.modelcontextprotocol.io | `mcp-publisher publish` (server.json, §2) |
| Smithery (smithery.ai) | `smithery.yaml` at root (shipped); claim the server on the site with the GitHub account |
| Glama (glama.ai/mcp/servers) | auto-indexes GitHub; `glama.json` at root (shipped) attributes maintainership; their bot verifies the server builds |
| Cline Marketplace | issue at cline/mcp-marketplace (§8) |
| mcp.so | "Submit" on the site with the repo URL |
| PulseMCP | auto-indexes from the official registry; their weekly digest takes tips |
| awesome-mcp-servers | PR — note the list now expects a Glama listing first |

## Verification (repo's own mechanisms, before any submission)

```sh
python3 -m py_compile hcl-ai/marvosa_mcp.py hcl-ai/marvosa_mcp_http.py
printf '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}\n{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"integrity","arguments":{}}}\n' \
  | python3 hcl-ai/marvosa_mcp.py          # expect alpha_inv 137.0 x3, intact True
sh mcp/make_mcpb.sh                        # bundle + sha256
sh verify_alpha.sh                         # substrate self-check
```
