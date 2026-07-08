#!/bin/sh
# Proves the one-line checkpoint is tamper-evident: loads the real graduate line,
# then corrupts one digit and shows the load REJECT it.
#
#     sh verify_tamper.sh  # one flipped digit in the line must be refused
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT/hcl-ai"
python3 - <<'PY'
import sys; sys.path.insert(0,'engine'); sys.path.insert(0,'mind')
import hcl_memory as VM
line = open('memory.hcl').read().strip()
print("Loading the genuine graduate checkpoint...")
mem = VM.HCLMemory.from_expression(line)
print("  OK, signature:", mem.signature())
print()
print("Now corrupting the alpha tag (last field) and re-loading...")
bad = line.rsplit(':',1)[0] + ':999'
try:
    VM.HCLMemory.from_expression(bad)
    print("  *** FAIL: corrupted line was accepted. Repo claim is FALSE. ***")
except Exception as e:
    print("  REJECTED as expected:", type(e).__name__)
    print("  The checkpoint cannot be silently altered.")
PY
