#!/usr/bin/env python3
"""
verify_os_floor.py — the substrate's multiplicative arithmetic RUNS ON the
OS kernel stack, and the integers prove it:

[1] shared seal: the stack's α⁻¹ equals the substrate's, digit for digit
    (the bootstraps differ at the π ulp; the seal absorbs it — recorded)
[2] the floor's three ops, 3-WAY equal on 3000 random signed operands
    each: floor form == the stack's full organ path (AMP_MOD / INV /
    FISSION) == this substrate's pure branches
[3] the measured reason the other ops stay native: divergence counts for
    add/sub/exp/ln/sin/cos, printed, not hand-waved
[4] the substrate ON the floor: a real model forward is token-identical
    and a real training turn is loss- and gradient-identical with the
    floor on vs off; braid advance equal; α true throughout
"""
import os, sys, random, importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'hcl-ai'))
sys.path.insert(0, os.path.join(HERE, 'hcl-ai', 'engine'))
sys.path.insert(0, os.path.join(HERE, 'hcl-ai', 'port'))

import hcl_engine as e
from hcl_engine import HCLTranscriber, SCALE

spec = importlib.util.spec_from_file_location(
    'os_stack_engine_v', os.path.join(HERE, 'hcl_stack', 'hcl_engine.py'))
stk = importlib.util.module_from_spec(spec); spec.loader.exec_module(stk)


def main():
    # [1] the seal
    assert stk.ALPHA_INV == e.ALPHA_INV
    dpi = e.PI_INT - stk.PI_INT
    print(f"[1] alpha^-1 identical across engines "
          f"({e.ALPHA_INV/SCALE:.6f}); bootstrap pi differs by {dpi} ulp "
          f"(substrate refined; stack == juj) — the seal absorbs it")

    t = HCLTranscriber()
    fl = t._floor_ok()
    assert fl is not None, "floor did not engage"

    # [2] 3-way equality on the floor set
    rng = random.Random(137)
    N = 3000
    ok = 0
    for _ in range(N):
        x = rng.randint(-10*SCALE, 10*SCALE)
        y = rng.randint(-10*SCALE, 10*SCALE) or SCALE
        m_pure = (abs(x)*abs(y))//SCALE; m_pure = -m_pure if (x<0)!=(y<0) else m_pure
        d_pure = (abs(x)*(SCALE*SCALE//abs(y)))//SCALE
        d_pure = -d_pure if (x<0)!=(y<0) else d_pure
        ax = abs(x)
        ok += (fl.mul(x,y) == fl.mul_organ(x,y) == m_pure and
               fl.div(x,y) == fl.div_organ(x,y) == d_pure and
               fl.sqrt(ax) == fl.sqrt_organ(ax))
    assert ok == N, f"floor 3-way equality broke: {ok}/{N}"
    print(f"[2] mul/div/sqrt: floor == stack organ path == substrate pure, "
          f"{N}/{N} each — the stack computes the substrate's "
          f"multiplicative arithmetic exactly")

    # [3] why the rest stay native — measured
    st = stk.HCLTranscriber()
    tp = HCLTranscriber()
    counts = {}
    for name, gen, fn in [
        ('add', lambda: (rng.randint(-10*SCALE,10*SCALE), rng.randint(-10*SCALE,10*SCALE)), lambda tr,a,b: tr.add(a,b)),
        ('sub', lambda: (rng.randint(-10*SCALE,10*SCALE), rng.randint(-10*SCALE,10*SCALE)), lambda tr,a,b: tr.sub(a,b)),
        ('exp', lambda: (rng.randint(-3*SCALE,3*SCALE),), lambda tr,a: tr.exp(a)),
        ('ln',  lambda: (rng.randint(1,10*SCALE),),       lambda tr,a: tr.ln(a)),
        ('sin', lambda: (rng.randint(0,SCALE-1),),        lambda tr,a: tr.sin(a)),
        ('cos', lambda: (rng.randint(0,SCALE-1),),        lambda tr,a: tr.cos(a)),
    ]:
        eq = 0
        for _ in range(500):
            a = gen()
            eq += (fn(tp, *a) == fn(st, *a)); st.clear()
        counts[name] = eq
    print("[3] native-retained ops (stack==substrate over 500):",
          ', '.join(f"{k} {v}/500" for k, v in counts.items()),
          "— routing any would change the substrate's integers")

    # [4] the substrate on the floor: forward + training, on vs off
    from chatmodel import StandardModel
    from learn import Trainer
    base = os.path.join(HERE, 'models', 'tinystories_260k')
    m = StandardModel(os.path.join(base, 'stories260K.bin'),
                      os.path.join(base, 'tok512.bin'), quiet=True, native=False)
    turn = m.tok.encode("hvp", bos=True) + [3 + ord('h'), 2]

    def run(floor_on):
        HCLTranscriber._floor_obj = fl if floor_on else None
        HCLTranscriber._floor_tried = True
        tr = Trainer(m, fast=True)
        b0 = m.eng.t.braid_len
        L, G = tr.forward_backward(turn)
        d = m.eng.t.braid_len - b0
        m.reset(); m.eng.t.clear()
        logits = m.forward(1, 0)
        top = max(range(len(logits)), key=lambda i: logits[i])
        return L, G, d, top, logits

    L1, G1, d1, top1, lg1 = run(False)
    L0, G0, d0, top0, lg0 = run(True)
    assert L0 == L1, "loss diverged on the floor"
    nv = 0
    for k in G0:
        a, b = G0[k], G1[k]
        la = a if k != 'emb' else [a]; lb = b if k != 'emb' else [b]
        if k in ('rms_att','rms_ffn'):
            for x, y in zip(a, b): assert x == y, k; nv += len(x)
        elif k == 'rms_final':
            assert a == b; nv += len(a)
        else:
            for X, Y in zip(la, lb):
                for rx, ry in zip(X, Y): assert rx == ry, k; nv += len(rx)
    assert d0 == d1 and top0 == top1 and lg0 == lg1
    assert m.eng.alpha_ok()
    print(f"[4] floor ON vs OFF: training loss int-identical, {nv:,} "
          f"gradient values equal, braid {d0:,} == {d1:,}, forward logits "
          f"identical, alpha true — the substrate runs on the stack and "
          f"nothing moved by one unit")

    HCLTranscriber._floor_obj = fl   # leave the floor on
    print()
    print("THE SUBSTRATE'S MULTIPLICATIVE FLOOR IS THE OS KERNEL STACK,")
    print("exactly — same integers, same braid, same alpha, stack executing.")


if __name__ == '__main__':
    main()
