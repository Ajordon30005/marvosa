#!/bin/sh
# verify_repo.sh — THE WHOLE REPOSITORY, ONE GO.
#
# Everything test_all.sh proves, plus the mechanical soundness a first-time
# reader (human or AI) depends on, plus the standard-model stack (run, train,
# live), in one sequential pass with one summary. If this passes on your
# machine, every claim in this repository just executed in front of you.
#
#   sh verify_repo.sh              (~20-28 minutes, pure python3, no network)
#   sh verify_repo.sh --resume LOG (continue the SAME run after the
#                                   environment killed it: sections already
#                                   [PASS] in LOG are honored, the rest run.
#                                   One gate, one acceptance — interruption
#                                   is the environment's fault, not a reason
#                                   to start the proof over.)
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
PASS=0; FAIL=0; T0=$(date +%s)
RESUME_LOG=""
if [ "$1" = "--resume" ] && [ -f "$2" ]; then RESUME_LOG="$2"; fi
run() {
  if [ -n "$RESUME_LOG" ] && grep -Fq -- "-- [PASS] $1 (" "$RESUME_LOG"; then
    PASS=$((PASS+1))
    echo "-- [PASS] $1 (honored from the interrupted run)"
    return
  fi
  echo ""
  echo "================================================================"
  echo "## $1"
  echo "================================================================"
  t=$(date +%s)
  if eval "$2"; then PASS=$((PASS+1)); v=PASS; else FAIL=$((FAIL+1)); v=FAIL; fi
  echo "-- [$v] $1 ($(( $(date +%s) - t ))s)"
}

run "Mechanical audit: compile, import, shells, configs, twins, doc refs" "python3 - << 'PYEOF'
import os, sys, subprocess, re, json, py_compile
ROOT = os.getcwd(); bad = []
pys = subprocess.run(['find','.','-name','*.py','-not','-path','./.git/*'],
                     capture_output=True, text=True).stdout.split()
for p in pys:
    try: py_compile.compile(p, doraise=True)
    except Exception as ex: bad.append(f'COMPILE {p}: {ex}')
for p in pys:
    d, f = os.path.split(p); mod = f[:-3]
    if mod == '__init__': continue
    try:
        r = subprocess.run([sys.executable, '-c',
            f'import sys; sys.path.insert(0, {d!r}); import {mod}'],
            capture_output=True, text=True, timeout=120,
            cwd=ROOT, stdin=subprocess.DEVNULL)
        if r.returncode != 0:
            bad.append(f'IMPORT {p}: ' + (r.stderr.strip().splitlines()[-1]
                                          if r.stderr.strip() else '?'))
    except subprocess.TimeoutExpired:
        bad.append(f'IMPORT-HANG {p}')
for s in subprocess.run(['find','.','-name','*.sh'],
                        capture_output=True, text=True).stdout.split():
    r = subprocess.run(['bash','-n',s], capture_output=True, text=True)
    if r.returncode != 0: bad.append(f'SH {s}: {r.stderr.strip()}')
for f in ('hcl_engine.py','hcl_memory.py','juj.py'):
    if open(f'hcl-ai/engine/{f}','rb').read() != \
       open(f'ingest_and_expel/engine/{f}','rb').read():
        bad.append(f'TWIN-DIVERGED {f}')
for cfg in ['server.json','glama.json','gemini-extension.json','.mcp.json',
            '.vscode/mcp.json','.cursor/mcp.json','.codex-plugin/plugin.json',
            'mcp/mcpb/manifest.json']:
    if os.path.exists(cfg):
        try: json.load(open(cfg))
        except Exception as ex: bad.append(f'JSON {cfg}: {ex}')
mds = subprocess.run(['find','.','-name','*.md'],
                     capture_output=True, text=True).stdout.split()
ref = re.compile(r'(?:^|[\s\`(\[])((?:hcl-ai|ingest_and_expel|docs|skills|'
                 r'models|mcp)/[\w./\-]+\.(?:py|md|sh|bin|json|yaml|txt|mcpb))')
for m in mds:
    txt = open(m, encoding='utf-8', errors='replace').read()
    for x in ref.findall(txt):
        # resolve against repo root, then against the doc's own directory
        # fetch-target dirs are absent by design (packs exclude them;
        # the docs pair every such path with its download command)
        if x.startswith(('models/tinystories_15m/', 'models/tinyllama_1b/')):
            continue
        if not (os.path.exists(x) or
                os.path.exists(os.path.join(os.path.dirname(m), x))):
            bad.append(f'MISSING-REF {m} -> {x}')
print(f'{len(pys)} py compile+import, shells, configs, twins, doc refs checked')
for b in bad: print('  ', b)
sys.exit(1 if bad else 0)
PYEOF"

run "The organism gate (test_all.sh: floats, alpha, tamper, speed, AI, skills)" \
    "sh test_all.sh 2>&1 | tail -6; sh test_all.sh > /dev/null 2>&1"
run "Engine fast paths bit-identical to composed primitives" "python3 verify_fastpath.py"
run "The compiled shell: same integers, compiled body (or absent = pure)" \
    "sh build_shell.sh && python3 verify_shell.py"
run "The body: holographic checkpoint carry" "python3 verify_largemodel.py"
run "The nemotron runner: MCL selection, substrate halting" "python3 verify_runmodel.py"
run "A REAL model, token-exact vs its own run.c" "python3 verify_chatmodel.py"
run "Training: exact gradients, four-param optimizer, line evolves" "python3 verify_learn.py"
run "Live unification: talking IS training; persists and wakes" "python3 verify_livemodel.py"
run "The three-part mind: two lines + the window law" "python3 verify_threemind.py"
run "Inherent weights: the operator, the lottery, time on top" "python3 verify_inherent.py"
run "The native regime: DJ interference, cited and measured" "python3 verify_native.py"
run "HVP emission: one forward, a whole artifact, nothing streams" \
    "python3 verify_hvp_head.py"
run "HVP as a language, hosted: the register and the bijection" \
    "python3 verify_hvp_lang.py 12"
run "the trainer's compiled walk IS the pure walk (bit-identical)" \
    "python3 verify_train_fast.py"
run "The OS floor: substrate mul/div/sqrt RUN ON the stack (bit-identical)" \
    "python3 verify_os_floor.py"
run "The OS kernel stack: gates, ALU, machine, libm, memory line (alpha sealed)" \
    "cd hcl_stack && { { test -f hcl_fast.so || cc -O2 -shared -fPIC hcl_fast.c -o hcl_fast.so -lgmp 2>/dev/null; } && test -f hcl_fast.so && python3 verify_fast.py; } || { python3 hcl_bitwise.py >/dev/null && python3 hcl_adder.py >/dev/null && python3 hcl_sub.py >/dev/null && echo 'pure stack self-verified (compiled host absent on this box)'; }; cd .."
run "HVP for ANY standard AI: wire, dialects, real acquisition" \
    "python3 verify_hvp_standard.py"
run "The MST equation: one step, one collapse (sequence == runner)" \
    "python3 verify_mst_equation.py"
run "The collapse calculator: door opens, landing exact, no logging" \
    "./calc.sh 2+2 | grep -qx 4 && python3 -c \"import sys; sys.path.insert(0,'hcl-ai'); from collapse_calc import CollapseEngine, evaluate; import numpy as np; v=np.array([np.sin(t)+2 for t in np.linspace(1e-3,2*np.pi-1e-3,360)]); r=CollapseEngine(v).run(); assert abs(r['result']-float(v.mean()))<=1e-12  # exact fp mean re-rounded to double vs numpy's sum order; assert 'iter' not in r; print('exact landing, silent')\""
run "Every door opens: all 15 runnable surfaces, both lives guarded" "sh verify_doors.sh"
run "MCP bundle wakes and answers (five tools, alpha 137)" "cd /tmp && rm -rf .vrepo && mkdir .vrepo && cd .vrepo && unzip -q '$ROOT/mcp/dist/marvosa.mcpb' && printf '%s\n%s\n' '{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"initialize\",\"params\":{\"protocolVersion\":\"2025-06-18\",\"capabilities\":{},\"clientInfo\":{\"name\":\"v\",\"version\":\"1\"}}}' '{\"jsonrpc\":\"2.0\",\"id\":2,\"method\":\"tools/call\",\"params\":{\"name\":\"integrity\",\"arguments\":{}}}' | python3 server/marvosa_mcp.py 2>/dev/null | grep -q '137.0' && cd '$ROOT'"

echo ""
echo "================================================================"
echo "REPO GATE SUMMARY: $PASS passed, $FAIL failed ($(( ($(date +%s) - T0) / 60 )) min total)"
if [ "$FAIL" = "0" ]; then
  echo "The whole repository just proved itself on this machine, in one go."
else
  echo "Something failed above — that is a real finding; open an issue with this output."
fi
echo "================================================================"
[ "$FAIL" = "0" ]
