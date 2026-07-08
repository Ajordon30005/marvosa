#!/bin/sh
# Builds mcp/dist/marvosa.mcpb — a real MCP Bundle (zip with manifest.json at
# root) for one-click install in Claude Desktop (Settings -> Extensions) and
# for the official MCP registry's mcpb package type (server.json).
#
# Layout inside the bundle:
#   manifest.json
#   server/            <- exact mirror of hcl-ai/ so every __file__-anchored
#                         path (engine/, mind/, memory.hcl) resolves unchanged
#
# After building, this prints the SHA-256 of the bundle. Paste that hash into
# server.json (fileSha256) before publishing to the official MCP registry,
# and attach the bundle to the matching GitHub release (v1.1.0).
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DIST="$ROOT/mcp/dist"
STAGE="$DIST/.stage"
rm -rf "$STAGE" "$DIST/marvosa.mcpb"
mkdir -p "$STAGE/server"
cp "$ROOT/mcp/mcpb/manifest.json" "$STAGE/manifest.json"
cp "$ROOT/hcl-ai/marvosa_mcp.py"      "$STAGE/server/"
cp "$ROOT/hcl-ai/marvosa_mcp_http.py" "$STAGE/server/"
cp "$ROOT/hcl-ai/memory.hcl"          "$STAGE/server/"
[ -f "$ROOT/hcl-ai/lifebook.txt" ]  && cp "$ROOT/hcl-ai/lifebook.txt"  "$STAGE/server/"
[ -f "$ROOT/hcl-ai/prior.txt" ]     && cp "$ROOT/hcl-ai/prior.txt"     "$STAGE/server/"
[ -f "$ROOT/hcl-ai/gradebook.txt" ] && cp "$ROOT/hcl-ai/gradebook.txt" "$STAGE/server/"
cp -r "$ROOT/hcl-ai/engine" "$STAGE/server/engine"
cp -r "$ROOT/hcl-ai/mind"   "$STAGE/server/mind"
find "$STAGE" -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true
( cd "$STAGE" && zip -rq "$DIST/marvosa.mcpb" . )
rm -rf "$STAGE"
echo "built: $DIST/marvosa.mcpb"
if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$DIST/marvosa.mcpb"
else
    shasum -a 256 "$DIST/marvosa.mcpb"
fi
