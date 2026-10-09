#!/usr/bin/env python3
"""
verify_train_fast.py — the trainer's compiled walk IS the pure walk:

[1] one full forward_backward, fast vs pure, same turn, same weights:
    loss integers EQUAL; every gradient tensor EQUAL element-for-element
    (emb, rms_att, rms_ffn, rms_final, wq, wk, wv, wo, w1, w2, w3);
    braid-length advance EQUAL; alpha sealed on both
[2] target_weights stratification: a mixed-weight turn (external ONE +
    a zeroed position) — equal again, including the zero-skip parity
[3] one apply() from the shared grads, then a second fast walk from the
    updated weights — the packed cache invalidates correctly and the
    walk still equals the pure walk after the step
[4] speed, printed not promised

Exact means int == int. The pure loops remain the ground truth.
"""
import os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'hcl-ai'))
sys.path.insert(0, os.path.join(HERE, 'hcl-ai', 'engine'))
sys.path.insert(0, os.path.join(HERE, 'hcl-ai', 'port'))

from chatmodel import StandardModel
from learn import Trainer

BASE = os.path.join(HERE, 'models', 'tinystories_260k')


def eq_grads(Ga, Gb):
    n = 0
    for k in Ga:
        a, b = Ga[k], Gb[k]
        if k == 'rms_final':
            assert a == b, k
            n += len(a)
        elif k in ('rms_att', 'rms_ffn'):
            for la, lb in zip(a, b):
                assert la == lb, k
                n += len(la)
        else:
            layers_a = a if k != 'emb' else [a]
            layers_b = b if k != 'emb' else [b]
            for La, Lb in zip(layers_a, layers_b):
                for ra, rb in zip(La, Lb):
                    assert ra == rb, k
                    n += len(ra)
    return n


def main():
    m = StandardModel(os.path.join(BASE, 'stories260K.bin'),
                      os.path.join(BASE, 'tok512.bin'),
                      quiet=True, native=False)
    pure = Trainer(m, fast=False)
    fast = Trainer(m, fast=True)
    assert fast.fast, "shell missing — build it: sh build_shell.sh"

    turn = m.tok.encode("hvp alpha", bos=True) + [3 + b for b in b"hi"] + [2]

    # [1] full walk equality
    # the transcriber's braid_len is the global generator counter — its
    # advance across a call is the walk's exact length (braid_ops is each
    # trainer's own ledger of the same counter, not an independent count)
    b0 = m.eng.t.braid_len
    t0 = time.time(); Lp, Gp = pure.forward_backward(turn); tp = time.time() - t0
    d_pure = m.eng.t.braid_len - b0
    b0 = m.eng.t.braid_len
    t0 = time.time(); Lf, Gf = fast.forward_backward(turn); tf = time.time() - t0
    d_fast = m.eng.t.braid_len - b0
    assert Lf == Lp, "loss diverged"
    nvals = eq_grads(Gp, Gf)
    assert d_fast == d_pure, (d_fast, d_pure)
    assert m.eng.alpha_ok()
    print(f"[1] full walk equal: loss int-identical; {nvals:,} gradient "
          f"values equal; braid advance {d_pure:,} == {d_fast:,}; alpha ok")

    # [2] stratified weights with a zeroed position
    tw = [pure.ONE] * (len(turn) - 1)
    tw[1] = 0
    Lp2, Gp2 = pure.forward_backward(turn, target_weights=tw)
    Lf2, Gf2 = fast.forward_backward(turn, target_weights=tw)
    assert Lf2 == Lp2
    eq_grads(Gp2, Gf2)
    print("[2] stratified turn equal (zeroed position skipped identically)")

    # [3] apply, then walk again — packed cache must refresh
    fast.apply(Gp)
    Lp3, Gp3 = pure.forward_backward(turn)
    Lf3, Gf3 = fast.forward_backward(turn)
    assert Lf3 == Lp3
    eq_grads(Gp3, Gf3)
    print("[3] after apply(): walks still equal — cache invalidation holds")

    # [4] speed
    print(f"[4] this turn ({len(turn)} tokens): pure {tp:.1f}s, "
          f"fast {tf:.1f}s — {tp / tf:.1f}x")
    print()
    print("FAST WALK == PURE WALK, EXACTLY. Same integers, same braid")
    print("counts, same alpha — the walk just stopped paying the host tax.")


if __name__ == '__main__':
    main()
