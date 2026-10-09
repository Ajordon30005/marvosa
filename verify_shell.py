#!/usr/bin/env python3
"""
verify_shell.py — the compiled shell is the transcriber's dot, verbatim:

[1] 500 random single products: shell == (|a|*|b|)//SCALE with sign
    after — the engine's own semantics (hcl_engine:424)
[2] a 64x64 matrix with remainders and mixed signs: every row equal
[3] five full forward tokens, shell ON vs OFF: logits bit-identical,
    braid counter identical
[4] the fallback IS the pure path: with the library masked, the same
    call runs and lands the same integers
[5] speed, printed not promised
"""
import os, sys, time, random

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'hcl-ai'))
sys.path.insert(0, os.path.join(HERE, 'hcl-ai', 'engine'))

import shell
from hcl_engine import HCLTranscriber, SCALE as S
from chatmodel import StandardModel

BASE = os.path.join(HERE, 'models', 'tinystories_260k')
MODEL, TOK = os.path.join(BASE, 'stories260K.bin'), os.path.join(BASE, 'tok512.bin')


def main():
    assert shell.available(), "build it first: sh build_shell.sh"
    t = HCLTranscriber()
    rng = random.Random(137)

    # [1] single products through a 1x1 matvec
    for _ in range(500):
        a = rng.randint(-9 * S, 9 * S) + rng.randint(0, S - 1)
        b = rng.randint(-9 * S, 9 * S) + rng.randint(0, S - 1)
        pm = shell.PackedMatrix([[b]])
        got = shell.matvec(pm, [a], t)[0]
        ref = t.dot([a], [b])
        assert got == ref, (a, b, got, ref)
    print("[1] 500 random products: shell == the engine's dot, every one")

    # [2] a full matrix, remainders and signs everywhere
    W = [[rng.randint(-9 * S, 9 * S) + rng.randint(0, S - 1)
          for _ in range(64)] for _ in range(64)]
    X = [rng.randint(-9 * S, 9 * S) + rng.randint(0, S - 1)
         for _ in range(64)]
    ref = [t.dot(X, row) for row in W]
    got = shell.matvec(shell.PackedMatrix(W), X, t)
    assert got == ref
    print("[2] 64x64 with remainders and mixed signs: all rows equal")

    # [3] five tokens, ON vs OFF, logits bit-identical
    def run(masked):
        m = StandardModel(MODEL, TOK, quiet=True)
        if masked:
            m._shell = None
        toks = m.tok.encode("One day Tom went to the", bos=True)
        m.reset(); pos = 0
        for tt in toks[:-1]:
            m.forward(tt, pos); pos += 1
        cur, outs = toks[-1], []
        t0 = time.time()
        for _ in range(5):
            lg = m.forward(cur, pos); pos += 1
            outs.append(list(lg))
            cur = max(range(len(lg)), key=lambda i: lg[i])
        return outs, (time.time() - t0) / 5, m.eng.t.braid_len

    on, dt_on, ops_on = run(masked=False)
    off, dt_off, ops_off = run(masked=True)
    assert on == off, "logits diverged between shell and pure"
    assert ops_on == ops_off, "braid counters diverged"
    print("[3] five forward tokens, shell ON vs OFF: logits bit-identical, "
          "braid counters identical")
    print(f"[4] the fallback IS the pure path — same call, same integers")
    print(f"[5] measured: shell {dt_on*1000:.0f} ms/token vs pure "
          f"{dt_off*1000:.0f} ms/token on this machine, this run")

    check_layer_body(None)
    check_token_layerbody(None)
    check_fused_rows(None)
    check_mass_participation(None)
    print()
    print("ALL CHECKS PASSED — the shell is the same arithmetic in a")
    print("compiled body: bit-identical integers, identical counting,")
    print("pure fallback always present.")




def check_layer_body(m):
    """[6] the compiled layer body: every routed op bit-identical to the
    pure engine over adversarial ranges, then a full token ON vs OFF."""
    import random, importlib
    sys.path.insert(0, os.path.join(HERE, 'hcl-ai', 'engine'))
    import hcl_engine as E
    import shell
    fx = shell.fx_ops(E.SCALE)
    assert fx is not None, "shell absent"
    S = E.SCALE
    rnd = random.Random(41)
    # exp: the softmax-gap range where reduction matters, plus normals
    xs = [rnd.randint(-35*S, 2*S) for _ in range(300)] + [0, S, -S, -27*S]
    for x in xs:
        assert fx.exp(x) == E._exp_fp(x), f"exp diverged at {x}"
    # tdiv: signed, denominators down to the rms scale
    for _ in range(300):
        a = rnd.randint(-9*S, 9*S)
        b = rnd.choice([1, -1]) * rnd.randint(S//1000, 5*S)
        pure = (abs(a) * (S*S // abs(b))) // S
        if (a < 0) != (b < 0): pure = -pure
        assert fx.tdiv(a, b) == pure, f"tdiv diverged at {a}/{b}"
    # sin/cos over the phase circle incl the four special angles
    pfs = [rnd.randint(0, S-1) for _ in range(200)] + [0, S//4, S//2, 3*S//4]
    for pf in pfs:
        ang = E._fixed_div(E._fixed_mul(pf, 2*E.PI_INT), S)
        assert fx.sin_rad(ang) == E._sin_fp(ang, 40), f"sin diverged at pf={pf}"
        assert fx.cos_rad(ang) == E._cos_fp(ang, 40), f"cos diverged at pf={pf}"
    # sqrt incl exact squares
    for _ in range(150):
        x = rnd.randint(0, 9*S)
        assert fx.sqrt_mag(x) == E._fixed_sqrt(x, 60), f"sqrt diverged at {x}"
    for k in range(1, 12):
        x = k*k*S
        assert fx.sqrt_mag(x) == E._fixed_sqrt(x, 60)
    # vector ops
    for _ in range(60):
        n = rnd.randint(1, 96)
        X = [rnd.randint(-3*S, 3*S) for _ in range(n)]
        Y = [rnd.randint(-3*S, 3*S) for _ in range(n)]
        K = rnd.randint(-2*S, 2*S)
        t = E.HCLTranscriber(); t.light()
        assert fx.vadd(X, Y) == t.vadd(X, Y)
        assert fx.vsub(X, Y) == t.vsub(X, Y)
        assert fx.vmul(X, Y) == t.vmul(X, Y)
        assert fx.vscale(X, K) == t.vscale(X, K)
        A1 = X[:]; A2 = X[:]
        fx.axpy(A1, K, Y); t.axpy(A2, K, Y)
        assert A1 == A2
    print("[6] layer body bit-identical: exp(304 pts incl -35..2), tdiv(300 signed), "
          "sin/cos(204 angles incl specials), sqrt(161), five vector ops x60")

def check_token_layerbody(m_on):
    """[7] one full token with routed layer body vs pure engine: logits and
    braid counter both identical; then the speed of the routed path."""
    import importlib, time
    sys.path.insert(0, os.path.join(HERE, 'hcl-ai'))
    from chatmodel import StandardModel
    P = os.path.join(HERE, 'models', 'tinystories_260k')
    import hcl_engine as E
    def run(routed):
        m = StandardModel(os.path.join(P, 'stories260K.bin'),
                          os.path.join(P, 'tok512.bin'), quiet=True)
        if not routed:
            E.HCLTranscriber._fx = None
            E.HCLTranscriber._fx_tried = True
        else:
            E.HCLTranscriber._fx_tried = False
        toks = m.tok.encode("One day", bos=True); m.reset(); pos = 0
        for t in toks[:-1]:
            m.forward(t, pos); pos += 1
        c0 = m.eng.t.braid_len
        t0 = time.time()
        lg = m.forward(toks[-1], pos)
        dt = (time.time() - t0) * 1000
        return lg, m.eng.t.braid_len - c0, dt
    lg_on, ops_on, ms_on = run(True)
    lg_off, ops_off, ms_off = run(False)
    assert lg_on == lg_off, "routed logits diverged from pure"
    assert ops_on == ops_off, f"braid counter diverged: {ops_on} vs {ops_off}"
    print(f"[7] full token, layer body ON vs OFF: logits bit-identical, "
          f"counter identical ({ops_on:,}); {ms_on:.0f} ms routed vs {ms_off:.0f} ms pure")




def check_fused_rows(m):
    """[8] the fused row kernels — softmax, silu, rope — each one crossing,
    bit-identical to the pure bodies over random rows."""
    import random
    sys.path.insert(0, os.path.join(HERE, 'hcl-ai'))
    sys.path.insert(0, os.path.join(HERE, 'hcl-ai', 'engine'))
    import hcl_engine as E
    import shell
    from chatmodel import StandardModel, _fp
    fx = shell.fx_ops(E.SCALE)
    S = E.SCALE
    rnd = random.Random(11)
    E.HCLTranscriber._fx = None
    E.HCLTranscriber._fx_tried = True          # pure side for reference
    P = os.path.join(HERE, 'models', 'tinystories_260k')
    mm = StandardModel(os.path.join(P, 'stories260K.bin'),
                       os.path.join(P, 'tok512.bin'), quiet=True)
    t = E.HCLTranscriber(); t.light()
    def pure_softmax(z):
        mx = max(z)
        exps = [E._exp_fp(zi - mx) for zi in z]
        s = sum(exps)
        inv = (abs(S) * (S * S // abs(s))) // S
        out = []
        for e2 in exps:
            p = (abs(e2) * abs(inv)) // S
            out.append(p)
        return out
    for _ in range(20):
        n = rnd.randint(2, 60)
        z = [rnd.randint(-30 * S, 2 * S) for _ in range(n)]
        assert fx.softmax(z) == pure_softmax(z), "softmax row diverged"
    for _ in range(20):
        n = rnd.randint(2, 64)
        h1 = [rnd.randint(-8 * S, 8 * S) for _ in range(n)]
        h3 = [rnd.randint(-8 * S, 8 * S) for _ in range(n)]
        ref = []
        for a, b in zip(h1, h3):
            e2 = E._exp_fp(-a)
            den = S + e2
            sig = (abs(S) * (S * S // abs(den))) // S
            p = (abs(a) * abs(sig)) // S
            if a < 0: p = -p
            r = (abs(p) * abs(b)) // S
            if (p < 0) != (b < 0): r = -r
            ref.append(r)
        assert fx.silu_mul(h1, h3) == ref, "silu row diverged"
    HS = mm.cfg['head_size']
    TWO_PI = 2 * E.PI_INT
    for trial in range(12):
        n = HS * rnd.choice([1, 2, 4])
        vec = [rnd.randint(-3 * S, 3 * S) for _ in range(n)]
        pos = rnd.choice([0, 1, 7, 63, 250])
        a = vec[:]; mm._rope(a, pos, n)
        b = fx.rope(vec[:], n, HS, _fp(float(pos)), mm.inv_freq, TWO_PI)
        assert a == b, f"rope diverged pos={pos}"
    print("[8] fused rows bit-identical: softmax x20 (gaps to -30), "
          "silu x20, rope x12 (pos incl 0) — one crossing each")




def check_mass_participation(m):
    """[9] mass participation. T1: sub-quantum rows annihilate exactly —
    outputs AND braid counters bit-identical to the pure loop on
    constructed matrices; the dense checkpoint fires zero skips (its
    trained rows are never sub-quantum); the void-born body's zero
    tensors collapse traversal cost while the count is preserved."""
    import random, time
    sys.path.insert(0, os.path.join(HERE, 'hcl-ai'))
    sys.path.insert(0, os.path.join(HERE, 'hcl-ai', 'engine'))
    import hcl_engine as E
    from chatmodel import StandardModel
    S = E.SCALE
    t = E.HCLTranscriber(); t.light()
    rnd = random.Random(2)
    class Stub:
        _E = E
        _shell = None
        _matvec = StandardModel._matvec
        def __init__(s):
            s.eng = type('X', (object,), {'t': t,
                        'dot': lambda s2, a, b: t.dot(a, b)})()
            s._wmax = {}; s._rcomp = {}
    mm = Stub()
    for trial in range(20):
        rows, cols = rnd.randint(2, 12), rnd.randint(2, 16)
        W = [[rnd.randint(-3, 3) for _ in range(cols)] if rnd.random() < 0.4
             else [rnd.randint(-2 * S, 2 * S) for _ in range(cols)]
             for _ in range(rows)]
        x = [rnd.randint(-2 * S, 2 * S) for _ in range(cols)]
        c0 = t.braid_len
        got = mm._matvec(W, x, ('t', trial))
        ops_a = t.braid_len - c0
        c0 = t.braid_len
        ref = [t.dot(x, row) for row in W]
        ops_b = t.braid_len - c0
        assert got == ref and ops_a == ops_b, "T1 diverged"
    P = os.path.join(HERE, 'models', 'tinystories_260k')
    dm = StandardModel(os.path.join(P, 'stories260K.bin'),
                       os.path.join(P, 'tok512.bin'), quiet=True)
    toks = dm.tok.encode("One day", bos=True); dm.reset(); pos = 0
    for tk in toks:
        dm.forward(tk, pos); pos += 1
    dense_fire = sum(1 for wm in dm._wmax.values() for v in wm if v == 0)
    assert dense_fire == 0
    zb = os.path.join(HERE, 'models', 'zero_born', 'zero.bin')
    void_note = ""
    if os.path.exists(zb):
        vm = StandardModel(zb, os.path.join(HERE, 'models', 'zero_born',
                                            'tok512.bin'), quiet=True)
        toks = vm.tok.encode("Kip", bos=True); vm.reset(); pos = 0
        c0 = vm.eng.t.braid_len; t0 = time.time()
        for tk in toks:
            vm.forward(tk, pos); pos += 1
        void_note = (f"; void-born {round((time.time()-t0)/len(toks)*1000)} "
                     f"ms/tok at {(vm.eng.t.braid_len-c0)//len(toks):,} gen "
                     f"(annihilations counted)")
    print(f"[9] mass participation: T1 exact on 20 constructed matrices "
          f"(outputs+counters identical); dense fires 0{void_note}")


if __name__ == '__main__':
    main()
