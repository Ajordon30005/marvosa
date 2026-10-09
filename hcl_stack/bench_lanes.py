"""
bench_lanes.py — the same engine, two hosts, measured.
Python-host numbers are re-measured live; compiled-host numbers come from
loops that run entirely inside hcl_fast.so (same formulas, proven exact
by verify_fast.py).
"""
import ctypes, os, time, random
import hcl_engine as h

L = ctypes.CDLL(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             'hcl_fast.so'))
for f in ('hf_bench_prim', 'hf_bench_organ', 'hf_bench_memline'):
    getattr(L, f).restype = ctypes.c_double
L.hf_bench_prim.argtypes = [ctypes.c_int, ctypes.c_long]
L.hf_bench_organ.argtypes = [ctypes.c_long]
L.hf_bench_memline.argtypes = [ctypes.c_long]

S = h.SCALE
rng = random.Random(137)
D = 64
W = [rng.randint(-S, S) for _ in range(D)]
x = [rng.randint(-S, S) for _ in range(D)]

t0 = time.time(); R = 1500
for _ in range(R):
    acc = 0
    for j in range(D):
        acc += h._fixed_mul(W[j], x[j])
py_prim = D * R / (time.time() - t0)

t = h.HCLTranscriber()
va, vb = rng.randint(0, S), -rng.randint(0, S)
t0 = time.time(); R = 4000
for _ in range(R):
    t.add(t.mul(va, vb), va)
    t.clear()
py_organ = 2 * R / (time.time() - t0)

from hcl_machine import MemoryLine
mem = MemoryLine()
t0 = time.time(); R = 4000
for i in range(R):
    mem.write('A', 3, 23)
    mem.read('A')
py_mem = R / (time.time() - t0)

c_prim = L.hf_bench_prim(64, 40000)
c_organ = L.hf_bench_organ(200000)
c_mem = L.hf_bench_memline(200000)

print(f"{'lane':34}{'python host':>16}{'compiled host':>16}{'speedup':>9}")
for name, p, c in (
        ("primitive (_fixed_mul + add)", py_prim, c_prim),
        ("organ (AMP_MOD + COMP)", py_organ, c_organ),
        ("memory line (write + exact read)", py_mem, c_mem)):
    unit = 'op/s' if 'line' not in name else 'rt/s'
    print(f"{name:34}{p:>13,.0f} {unit:>3}{c:>13,.0f} {unit:>3}{c/p:>8.1f}x")
