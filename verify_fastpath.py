"""
verify_fastpath.py — proves the transcriber's inlined scalar paths are
BIT-IDENTICAL to the composed FBit forms (COMP, COMP∘SHIFT, AMP_MOD,
AMP_MOD∘INV) across the full magnitude range, including the tiny-sum floor
behavior of COMP's square-then-root reconstruction. Then measures what the
thinned shell buys: same arithmetic, fewer Python frames, no per-op dict in
light mode.

Run:  python3 verify_fastpath.py          (seconds)
"""
import sys, os, random, time

HERE = os.path.dirname(os.path.abspath(__file__))
for sub in ('hcl-ai/engine', 'hcl-ai/port', 'hcl-ai'):
    sys.path.insert(0, os.path.join(HERE, sub))

import hcl_engine as E
from hcl_engine import HCL, FBit, SCALE, HCLTranscriber


def composed_add(X, Y):
    return HCL.COMP(FBit.from_scalar(X), FBit.from_scalar(Y)).to_scalar()

def composed_sub(X, Y):
    return HCL.COMP(FBit.from_scalar(X),
                    HCL.SHIFT(FBit.from_scalar(Y), -SCALE)).to_scalar()

def composed_mul(X, Y):
    return HCL.AMP_MOD(FBit.from_scalar(X), FBit.from_scalar(Y)).to_scalar()

def composed_div(X, Y):
    return HCL.AMP_MOD(FBit.from_scalar(X),
                       HCL.INV(FBit.from_scalar(Y))).to_scalar()


def main():
    t = HCLTranscriber()
    rng = random.Random(137)

    def sample():
        # magnitudes from far below the COMP floor (1e-25) to huge (1e5),
        # plus structural values: 0, ±1 ulp, ±SCALE, the sqrt(SCALE) edge
        exp = rng.uniform(-25, 5)
        v = int(10 ** (exp + 40))
        return rng.choice([v, -v])

    edges = [0, 1, -1, SCALE, -SCALE, SCALE // 2,
             int(SCALE ** 0.5), int(SCALE ** 0.5) + 1,
             10**19, 10**20, 10**21, -10**20]
    pairs = [(a, b) for a in edges for b in edges if b != 0]
    pairs += [(sample(), sample()) for _ in range(20000)]
    pairs = [(a, b if b != 0 else 1) for a, b in pairs]

    for name, fast, comp in (
            ('add', t.add, composed_add),
            ('sub', t.sub, composed_sub),
            ('mul', t.mul, composed_mul),
            ('div', t.div, composed_div)):
        bad = 0
        for a, b in pairs:
            if fast(a, b) != comp(a, b):
                bad += 1
                if bad < 4:
                    print(f"  MISMATCH {name}({a},{b})")
        assert bad == 0, f"{name}: {bad} mismatches"
        print(f"[fastpath] {name}: {len(pairs)} pairs bit-identical to the "
              f"composed form")
    t.clear()

    # dot: fused vs the composed loop, including negatives and tiny values
    for trial in range(200):
        n = rng.randrange(1, 90)
        xs = [sample() for _ in range(n)]
        ws = [sample() for _ in range(n)]
        acc = 0
        for x, w in zip(xs, ws):
            acc = composed_add(acc, composed_mul(x, w))
        assert t.dot(xs, ws) == acc
    t.clear()
    print(f"[fastpath] dot: 200 random vectors bit-identical to the "
          f"composed COMP-loop of AMP_MOD")

    # fused VECTOR compositions vs their composed loops (bit-identity)
    for trial in range(150):
        n = rng.randrange(1, 90)
        xs = [sample() for _ in range(n)]
        ys = [sample() for _ in range(n)]
        k = sample()
        assert t.vadd(xs, ys) == [t.add(a, b) for a, b in zip(xs, ys)]
        assert t.vsub(xs, ys) == [t.sub(a, b) for a, b in zip(xs, ys)]
        assert t.vmul(xs, ys) == [t.mul(a, b) for a, b in zip(xs, ys)]
        assert t.vscale(xs, k) == [t.mul(a, k) for a in xs]
        acc = list(ys)
        t.axpy(acc, k, xs)
        assert acc == [t.add(y, t.mul(x, k)) for x, y in zip(xs, ys)]
    t.clear()
    print(f"[fastpath] vadd/vsub/vmul/vscale/axpy: 150 random vectors "
          f"bit-identical to composed loops")

    # incremental factorials in _sin_fp/_cos_fp are exact by construction
    # (integer-valued fixed-points multiply without truncation); assert on
    # a sweep against the defining series relation via engine outputs
    for x in [E.SCALE // 7, 3 * E.SCALE, -2 * E.SCALE, E.SCALE, 0]:
        s2 = E._sin_fp(x)
        c2 = E._cos_fp(x)
        one = E._fixed_mul(s2, s2) + E._fixed_mul(c2, c2)
        assert abs(one - E.SCALE) < 10**24, (x, one)   # sin²+cos²=1 to prec
    print(f"[fastpath] sin/cos incremental factorials: pythagorean identity "
          f"holds to precision")

    # the 02_operations law, asserted directly on composed COMP:
    # same-phase -> exact sum; opposite -> exact |difference|
    for a, b in pairs[:4000]:
        assert composed_add(a, b) == a + b
        assert composed_sub(a, b) == a - b
    print(f"[fastpath] COMP collinear == the 02_operations stated law "
          f"(exact sum / exact difference), 4000 pairs")

    # alpha unchanged (the four params never entered these code paths)
    assert abs(E.ALPHA_INV / E.SCALE - 137) < 1
    print(f"[fastpath] alpha_inv = {E.ALPHA_INV / E.SCALE} — intact")

    # what the thinning buys, measured
    xs = [SCALE + i for i in range(64)]
    ws = [SCALE - i for i in range(64)]
    t.light()
    t0 = time.time()
    for _ in range(2000):
        t.dot(xs, ws)
    fused = time.time() - t0
    ops = 2000 * 128
    print(f"[speed] fused dot, light mode: {ops/fused/1e6:.2f}M generators/s "
          f"({fused/2000*1e6:.0f}µs per 64-wide dot)")
    print("\nALL CHECKS PASSED — same arithmetic, thinner shell.")


if __name__ == '__main__':
    main()
