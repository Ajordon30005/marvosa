# hcl_fast — the same engine on a compiled host

`hcl_fast.c` is `hcl_engine.py` transcribed to compiled arithmetic (GMP):
same PREC=40 decimal lattice, same series and term counts, same TINY break,
same floor divisions, same Newton control flow, same bootstrap. Zero new
math — only the host changes.

Proof (`verify_fast.py`, the repo's own port law):
- C bootstrap produces the IDENTICAL constants digit-for-digit
  (PI_INT, eta, lambda, gamma, beta, alpha, alpha^-1 = 137.0)
- 1,320 primitive + 1,155 organ random cases: exact equality, phase and
  amplitude, zero mismatches
- memory line recovers exactly on the compiled host

Measured on one box (`bench_lanes.py`):

    lane                                python host    compiled host   speedup
    primitive (_fixed_mul + add)        1.91 Mop/s     9.55 Mop/s      5.0x
    organ (AMP_MOD + COMP)              0.24 Mop/s     1.18 Mop/s      4.9x
    memory line (write + exact read)    0.21 M rt/s    1.20 M rt/s     5.6x

The measured ladder above this, same box, same decimal-lattice law:
inline 3-limb exact-accumulate dot ~73-90 Mop/s at PREC=40; and the
precision dial: int64 lattice 1.25 Gop/s (exact, beats a compiled float64
loop), int16 5.0, int8 8.58 Gop/s (beats numpy's BLAS). Precision is a
lattice choice; exactness holds at every rung.

Build:  gcc -O3 -march=native -shared -fPIC -o hcl_fast.so hcl_fast.c -lgmp
Verify: python3 verify_fast.py
Bench:  python3 bench_lanes.py
