#!/bin/sh
# Honest benchmark: integer fixed-point multiply vs float multiply, SAME interpreter.
# Prints the real ratio so you can judge "fast" against the right baseline.
#
#     sh verify_speed.sh   # the honest per-op ratio vs a hardware float multiply
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT/hcl-ai"
python3 - <<'PY'
import sys, time; sys.path.insert(0,'engine')
import hcl_engine as E
N = 200000
S = E.SCALE
a = 3*S; b = 7*S
t0=time.perf_counter()
for _ in range(N): E._fixed_mul(a,b)
ti=time.perf_counter()-t0
af=3.0; bf=7.0
t0=time.perf_counter()
for _ in range(N): af*bf
tf=time.perf_counter()-t0
print(f"integer fixed_mul : {ti/N*1e9:7.1f} ns/op")
print(f"float multiply    : {tf/N*1e9:7.1f} ns/op  (hardware-subsidized)")
print(f"ratio             : {ti/tf:5.1f}x")
print()
print("This is the honest STARTING price - the entry fee, not the race. Float speed")
print("is a hardware subsidy (silicon built for IEEE-754) and its per-op cost is flat")
print("forever: it never gets cheaper for what it has learned. The substrate's native")
print("cost curve bends DOWN with composed scale (thresholds shrink as lambda^w;")
print("coherent structure costs less each use - 01_theory.md, 05_proofs.md, and the")
print("README's 'scale of it, measured'). Judge the slope, not the snapshot.")
PY
