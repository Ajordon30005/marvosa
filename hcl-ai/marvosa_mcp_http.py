"""
marvosa_mcp_http.py — the same five organism tools over streamable HTTP
(MCP transport) on port 8848.

    python3 hcl-ai/marvosa_mcp_http.py   # serves http://127.0.0.1:8848/mcp
See mcp/PLATFORMS.md for clients that speak HTTP transport.
"""
#!/usr/bin/env python3
"""
marvosa_mcp_http.py — MCP streamable-HTTP server wrapping the HCL-Pure AI
organism. Same five tools, same organism, same handlers as marvosa_mcp.py
(imported verbatim — zero duplicated logic). Standard library only.

This is the transport for clients that only accept REMOTE MCP servers:

  ChatGPT           Settings -> Apps & Connectors -> Create (developer mode)
  Manus             Settings -> Connectors -> Custom MCP -> Direct configuration
  Copilot Studio    Add tool -> Model Context Protocol
  Llama Stack       toolgroups.register(..., mcp_endpoint={"uri": <url>/mcp})
  Gemini CLI        settings.json mcpServers: {"marvosa": {"httpUrl": <url>/mcp}}

Run:
    python3 hcl-ai/marvosa_mcp_http.py [port]        # default port 8848

Endpoints:
    POST /mcp   JSON-RPC 2.0 (MCP streamable HTTP; single-JSON responses)
    GET  /      health check ("marvosa-mcp alive")

The organism runs on localhost. To reach hosted clients (ChatGPT, Manus),
expose it over HTTPS with a tunnel (ngrok http 8848 / cloudflared tunnel)
or host it on a machine you control. The connector URL is then
https://<your-host>/mcp
"""

import sys, json, uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# Importing marvosa_mcp wakes the organism once and reuses its TOOLS and
# handle_request verbatim. Its stdout shield is harmless here (we never
# write to stdout; HTTP responses go over sockets).
sys.path.insert(0, __file__.rsplit('/', 1)[0] if '/' in __file__ else '.')
import marvosa_mcp as core

_SESSION = uuid.uuid4().hex   # single-organism server: one session for all


class MCPHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    # -- helpers --------------------------------------------------------
    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS, DELETE")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Accept, Authorization, Mcp-Session-Id, MCP-Protocol-Version")
        self.send_header("Access-Control-Expose-Headers", "Mcp-Session-Id")

    def _json(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Mcp-Session-Id", _SESSION)
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def _empty(self, code):
        self.send_response(code)
        self.send_header("Content-Length", "0")
        self.send_header("Mcp-Session-Id", _SESSION)
        self._cors()
        self.end_headers()

    # -- HTTP methods -----------------------------------------------------
    def do_OPTIONS(self):
        self._empty(204)

    def do_GET(self):
        if self.path in ("/", "/health"):
            body = b"marvosa-mcp alive"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(body)))
            self._cors()
            self.end_headers()
            self.wfile.write(body)
        else:
            # No standalone SSE stream is offered; 405 is the spec-sanctioned
            # answer for GET on the MCP endpoint in that case.
            self._empty(405)

    def do_DELETE(self):
        # Session termination — acknowledged; the organism itself persists
        # only through its own memory line, never through HTTP sessions.
        self._empty(200)

    def do_POST(self):
        if not self.path.rstrip("/").endswith("/mcp") and self.path != "/":
            self._empty(404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length)
            req = json.loads(raw.decode("utf-8"))
        except Exception:
            self._json(400, {"jsonrpc": "2.0", "id": None,
                             "error": {"code": -32700, "message": "Parse error"}})
            return

        if isinstance(req, list):                       # JSON-RPC batch
            responses = [r for r in (core.handle_request(m) for m in req) if r is not None]
            if responses:
                self._json(200, responses)
            else:
                self._empty(202)
            return

        resp = core.handle_request(req)
        if resp is None:                                # notification
            self._empty(202)
        else:
            self._json(200, resp)

    def log_message(self, fmt, *args):                  # quiet: stderr only
        sys.stderr.write("marvosa-mcp-http: " + (fmt % args) + "\n")


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8848
    server = ThreadingHTTPServer(("0.0.0.0", port), MCPHandler)
    sys.stderr.write(f"marvosa-mcp-http listening on http://0.0.0.0:{port}/mcp\n")
    server.serve_forever()


if __name__ == "__main__":
    main()
