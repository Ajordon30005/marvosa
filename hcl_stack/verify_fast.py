"""
verify_fast.py — the compiled host equals the Python engine EXACTLY.

The repo's own port proof (06_porting steps 7-8), applied to a host port:
[1] the C bootstrap produces the IDENTICAL constants — PI_INT, eta, lambda,
    gamma, beta, alpha, alpha^-1 — same integers, digit for digit
[2] every fixed-point primitive agrees exactly on random operands
[3] every organ (COMP, AMP_MOD, SHIFT, INV, FISSION, MOBIUS, LOG,
    PHASE_SIN/COS, RESONANCE) agrees exactly — phase AND amplitude —
    on random FBits, including negative and mixed-phase cases
[4] the memory line roundtrip on the compiled host recovers exactly

Exact means mpz == python int. Not close. Equal.
"""
import ctypes, random, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hcl_engine as h

L = ctypes.CDLL(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             'hcl_fast.so'))
L.hf_const.restype = ctypes.c_char_p
L.hf_const.argtypes = [ctypes.c_char_p]
L.hf_prim.restype = ctypes.c_char_p
L.hf_prim.argtypes = [ctypes.c_char_p] * 3
L.hf_op.restype = ctypes.c_char_p
L.hf_op.argtypes = [ctypes.c_char_p]*5 + [ctypes.c_long,
                                          ctypes.POINTER(ctypes.c_char_p)]

def c_const(name):
    return int(L.hf_const(name.encode()))

def c_prim(op, x, y=0):
    return int(L.hf_prim(op.encode(), str(x).encode(), str(y).encode()))

def c_op(op, a, b=None, aux=0):
    pa, aa = str(a.phase_frac).encode(), str(a.amp).encode()
    if isinstance(b, h.FBit):
        pb, ab = str(b.phase_frac).encode(), str(b.amp).encode()
    elif isinstance(b, int):
        pb, ab = str(b).encode(), b"0"
    else:
        pb, ab = b"0", b"0"
    amp_out = ctypes.c_char_p()
    pf = L.hf_op(op.encode(), pa, aa, pb, ab, aux, ctypes.byref(amp_out))
    return h.FBit(int(pf), int(amp_out.value))

rng = random.Random(137)
S = h.SCALE

# [1] identical constants
pairs = [('PI', h.PI_INT), ('ETA', h.ETA), ('LAMBDA', h.LAMBDA),
         ('GAMMA', h.GAMMA), ('BETA', h.BETA), ('ALPHA', h.ALPHA),
         ('ALPHA_INV', h.ALPHA_INV)]
for name, py in pairs:
    assert c_const(name) == py, name
print(f"[1] bootstrap identical: all 7 constants equal digit-for-digit; "
      f"alpha^-1 = {c_const('ALPHA_INV')/S}")

# [2] primitives, exact, random operands (signed)
n = 0
for _ in range(300):
    X = rng.randint(-3*S, 3*S); Y = rng.randint(-3*S, 3*S) or S
    assert c_prim('mul', X, Y) == h._fixed_mul(X, Y)
    assert c_prim('div', X, Y) == h._fixed_div(X, Y)
    n += 2
for _ in range(120):
    X = rng.randint(0, 5*S)
    assert c_prim('sqrt', X) == h._fixed_sqrt(X, 80); n += 1
for _ in range(120):
    X = rng.randint(-S, S)
    assert c_prim('arctan', X) == h._arctan_int(X, 80)
    assert c_prim('sin', X) == h._sin_fp(X, 40)
    assert c_prim('cos', X) == h._cos_fp(X, 40)
    assert c_prim('exp', X) == h._exp_fp(X, 60)
    n += 4
for _ in range(120):
    X = rng.randint(1, 6*S)
    assert c_prim('ln', X) == h._ln_fp(X, 150); n += 1
print(f"[2] primitives exact: {n} random cases, zero mismatches")

def rfb():
    return h.FBit(rng.randint(0, S - 1), rng.randint(0, 3*S))

# [3] organs, exact, phase AND amp
n = 0
for _ in range(150):
    a, b = rfb(), rfb()
    for op, ref in (('COMP', h.HCL.COMP(a, b)),
                    ('AMP_MOD', h.HCL.AMP_MOD(a, b))):
        got = c_op(op, a, b)
        assert (got.phase_frac, got.amp) == (ref.phase_frac, ref.amp), op
        n += 1
for _ in range(150):
    a = rfb(); C = rng.randint(-3*S, 3*S)
    ref = h.HCL.SHIFT(a, C); got = c_op('SHIFT', a, C)
    assert (got.phase_frac, got.amp) == (ref.phase_frac, ref.amp); n += 1
for _ in range(150):
    a = rfb()
    if a.amp:
        ref = h.HCL.INV(a); got = c_op('INV', a)
        assert (got.phase_frac, got.amp) == (ref.phase_frac, ref.amp); n += 1
    ref = h.HCL.FISSION(a)[0]; got = c_op('FISSION', a)
    assert (got.phase_frac, got.amp) == (ref.phase_frac, ref.amp); n += 1
for _ in range(80):
    a = h.FBit.from_scalar(rng.randint(-2*S, 2*S))
    ref = h.HCL.MOBIUS_GROWTH(a); got = c_op('MOB', a)
    assert (got.phase_frac, got.amp) == (ref.phase_frac, ref.amp); n += 1
for _ in range(80):
    a = h.FBit(0, rng.randint(1, 6*S))
    ref = h.HCL.LOG_EXTRACT(a); got = c_op('LOG', a)
    assert (got.phase_frac, got.amp) == (ref.phase_frac, ref.amp); n += 1
for _ in range(120):
    pf = rng.randint(0, S - 1); a = h.FBit(pf, S)
    assert c_op('PSIN', a).to_scalar() == \
        h.FBit.from_scalar(h.HCL.PHASE_SIN(pf)).to_scalar()
    assert c_op('PCOS', a).to_scalar() == \
        h.FBit.from_scalar(h.HCL.PHASE_COS(pf)).to_scalar()
    n += 2
for w in (1, 2, 3, 5, 8):
    a = rfb()
    ref = h.HCL.RESONANCE(a, w); got = c_op('RES', a, aux=w)
    assert (got.phase_frac, got.amp) == (ref.phase_frac, ref.amp); n += 1
print(f"[3] organs exact: {n} random cases, phase and amplitude equal")

# [4] memory line on the compiled host: RESONANCE write, SHIFT read, exact
for w, val in ((3, 23), (5, 19), (3, 200), (5, 7)):
    v = h.FBit.from_scalar(val * S)
    cell = c_op('RES', v, aux=w)
    rec = c_op('SHIFT', cell, 2 * 10 ** (w - 1) * S)
    assert rec.amp // S == val, (w, val)
print("[4] memory line on the compiled host: exact recovery at w=3 and w=5")

print()
print("COMPILED HOST == PYTHON ENGINE, EXACTLY. Same lattice, same braid,")
print("same alpha — only the host changed.")
