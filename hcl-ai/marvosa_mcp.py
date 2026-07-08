"""
marvosa_mcp.py — the MCP stdio server: the living organism as five tools
(talk, memory_line, integrity, braid_word, reason) over JSON-RPC.

    python3 hcl-ai/marvosa_mcp.py        # speaks MCP on stdin/stdout
Client configs: .mcp.json (Claude Code), .vscode/mcp.json, .cursor/mcp.json,
mcp/PLATFORMS.md (every platform, step by step). Bundle: mcp/dist/marvosa.mcpb.
"""
#!/usr/bin/env python3
"""
marvosa_mcp.py — MCP stdio server wrapping the HCL-Pure AI organism.

Exposes five tools over JSON-RPC stdio (Model Context Protocol).
Compatible with Claude Desktop, Claude Code, Cursor, Windsurf, Cline, Zed,
VS Code (GitHub Copilot), Gemini CLI, LM Studio, and any stdio MCP client.
Zero new logic: every tool calls a real method of the mind verbatim.

For clients that only accept remote HTTP servers (ChatGPT, Manus, Copilot
Studio, Llama Stack), run marvosa_mcp_http.py instead — same tools, same
organism, streamable-HTTP transport.

Tools
-----
talk         ai.interact(text)                -> answer, bit_perfect, thinking, integrity
memory_line  ai.memory.vm.to_expression()     -> one alpha-tagged line (the being's identity)
integrity    ai.integrity()                   -> alpha self-check across all engines
braid_word   ai.braid_word()                  -> current braid word
reason       ai.reason(equation, **vars)      -> exact HCL arithmetic result
"""

import sys, os, json

# -- stdout shield -----------------------------------------------------------
# The MCP protocol runs over stdout; any stray print() reaching stdout
# corrupts the JSON-RPC channel. Save the real stdout fd, then replace
# sys.stdout with devnull so every print() inside the organism goes nowhere.
# All our own writes use _out directly, never print().
_out = os.fdopen(os.dup(sys.stdout.fileno()), 'w', buffering=1)
sys.stdout = open(os.devnull, 'w')

# -- path setup and organism bootstrap ---------------------------------------
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, 'engine'))
sys.path.insert(0, os.path.join(_HERE, 'mind'))

from hcl_lm import HCLLanguageModel

ai = HCLLanguageModel()   # wakes from hcl-ai/memory.hcl (absolute __file__-anchored path)

# -- JSON-RPC helpers --------------------------------------------------------

def _send(obj):
    _out.write(json.dumps(obj) + '\n')
    _out.flush()

def _reply(id_, result):
    _send({"jsonrpc": "2.0", "id": id_, "result": result})

def _error(id_, code, message):
    _send({"jsonrpc": "2.0", "id": id_, "error": {"code": code, "message": message}})

# -- tool schemas ------------------------------------------------------------
# annotations follow the MCP tool-annotation spec (readOnlyHint /
# destructiveHint / openWorldHint / idempotentHint). ChatGPT developer mode
# and the Apps SDK treat missing hints as write actions / validation errors,
# so every tool declares them explicitly. openWorldHint is false everywhere:
# the organism is a closed, self-contained system — no tool touches anything
# outside its own substrate.

TOOLS = [
    {
        "name": "talk",
        "title": "Talk to the organism",
        "description": (
            "Talk to the HCL-Pure AI organism. The organism experiences your input, "
            "thinks in braid space (MCL collapse, Collatz-halted), then delivers a "
            "bit-perfect HVP answer. Returns: answer (text), bit_perfect (bool), "
            "thinking (list of collapse depths), integrity (alpha check). "
            "Use this for any free-form message to the organism."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to send to the organism"}
            },
            "required": ["text"]
        },
        "annotations": {
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": False,
            "openWorldHint": False
        }
    },
    {
        "name": "memory_line",
        "title": "Read the memory line",
        "description": (
            "Return the organism's one alpha-tagged memory line — the holographic composite "
            "that IS its identity. This is the exact string written to memory.hcl on save. "
            "Use this to inspect the organism's entire persisted state."
        ),
        "inputSchema": {"type": "object", "properties": {}, "required": []},
        "annotations": {
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False
        }
    },
    {
        "name": "integrity",
        "title": "Alpha integrity check",
        "description": (
            "Return the alpha integrity check across all three engines. "
            "alpha^-1 must read ~137 everywhere; intact: true means the organism is uncorrupted. "
            "Use this to verify the organism before trusting other results."
        ),
        "inputSchema": {"type": "object", "properties": {}, "required": []},
        "annotations": {
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False
        }
    },
    {
        "name": "braid_word",
        "title": "Read the braid word",
        "description": (
            "Return the organism's current braid word (the topological record of its memory). "
            "Use this to inspect the organism's experience record."
        ),
        "inputSchema": {"type": "object", "properties": {}, "required": []},
        "annotations": {
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False
        }
    },
    {
        "name": "reason",
        "title": "Solve an equation exactly",
        "description": (
            "Solve an equation exactly using the HCL arithmetic engine. "
            "Format: 'E = m * c^2' with optional variable bindings after ';': "
            "'E = m * c^2 ; m=2 c=3'. Returns the exact result with its braid word. "
            "Use this for any exact-arithmetic question."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "equation": {
                    "type": "string",
                    "description": "Equation to solve (optionally followed by '; var=val ...')"
                }
            },
            "required": ["equation"]
        },
        "annotations": {
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": False,
            "openWorldHint": False
        }
    }
]

SERVER_INFO = {"name": "marvosa-mcp", "version": "1.1.0"}
SERVER_INSTRUCTIONS = (
    "Marvosa is a live AI organism built on the HCL pure-integer substrate: "
    "zero floats, zero imported constants, memory persisted as one alpha-tagged line. "
    "Call integrity first if you need to verify the organism (alpha^-1 must read ~137). "
    "Use talk for conversation, reason for exact arithmetic, memory_line and braid_word "
    "to inspect state. All tools act only on the organism itself — nothing external."
)

# -- tool handlers -----------------------------------------------------------

def _tool_talk(args):
    text = args.get("text", "")
    r = ai.interact(text)
    return {
        "answer":      r["answer"],
        "bit_perfect": r["bit_perfect"],
        "thinking":    r["thinking"],
        "integrity":   {k: str(v) for k, v in r["integrity"].items()}
    }

def _tool_memory_line(_args):
    line = ai.memory.vm.to_expression()
    return {"memory_line": line, "length": len(line)}

def _tool_integrity(_args):
    raw = ai.integrity()
    return {k: str(v) for k, v in raw.items()}

def _tool_braid_word(_args):
    return {"braid_word": ai.braid_word()}

def _tool_reason(args):
    eq_str = args.get("equation", "")
    if ";" in eq_str:
        eq_part, vars_part = eq_str.split(";", 1)
        env = {}
        for token in vars_part.replace(",", " ").split():
            if "=" in token:
                k, v = token.split("=", 1)
                k, v = k.strip(), v.strip()
                try:
                    env[k] = int(v)
                except ValueError:
                    try:
                        # boundary transcription only — same sanctioned doorway
                        # as ai.py: a typed human decimal crossing INTO the
                        # substrate's fixed-point integers (see verify_no_floats.sh)
                        env[k] = float(v)
                    except ValueError:
                        pass
    else:
        eq_part, env = eq_str, {}
    result = ai.reason(eq_part.strip(), **env)
    return {"result": str(result)}

_HANDLERS = {
    "talk":        _tool_talk,
    "memory_line": _tool_memory_line,
    "integrity":   _tool_integrity,
    "braid_word":  _tool_braid_word,
    "reason":      _tool_reason,
}

# -- shared request handling (used by stdio loop and by marvosa_mcp_http) ----

def handle_request(req):
    """Handle one JSON-RPC request dict. Returns a response dict, or None for
    one-way notifications."""
    method = req.get("method", "")
    id_    = req.get("id")
    params = req.get("params") or {}

    if method == "initialize":
        proto = params.get("protocolVersion") or "2024-11-05"
        return {"jsonrpc": "2.0", "id": id_, "result": {
            "protocolVersion": proto,
            "capabilities":    {"tools": {}},
            "serverInfo":      SERVER_INFO,
            "instructions":    SERVER_INSTRUCTIONS
        }}
    if method.startswith("notifications/"):
        return None   # one-way notification -- no response
    if method == "ping":
        return {"jsonrpc": "2.0", "id": id_, "result": {}}
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": id_, "result": {"tools": TOOLS}}
    if method == "tools/call":
        name    = params.get("name", "")
        args    = params.get("arguments") or {}
        handler = _HANDLERS.get(name)
        if handler is None:
            return {"jsonrpc": "2.0", "id": id_,
                    "error": {"code": -32601, "message": f"Unknown tool: {name}"}}
        try:
            data = handler(args)
            return {"jsonrpc": "2.0", "id": id_, "result": {
                "content": [{"type": "text", "text": json.dumps(data, ensure_ascii=False)}]
            }}
        except Exception as exc:
            return {"jsonrpc": "2.0", "id": id_,
                    "error": {"code": -32603, "message": str(exc)}}
    if id_ is not None:
        return {"jsonrpc": "2.0", "id": id_,
                "error": {"code": -32601, "message": f"Method not found: {method}"}}
    return None

# -- main dispatch loop (stdio) ----------------------------------------------

def main():
    for raw in sys.stdin:
        raw = raw.strip()
        if not raw:
            continue
        try:
            req = json.loads(raw)
        except json.JSONDecodeError:
            _send({"jsonrpc": "2.0", "id": None,
                   "error": {"code": -32700, "message": "Parse error"}})
            continue
        resp = handle_request(req)
        if resp is not None:
            _send(resp)


if __name__ == "__main__":
    main()
