"""
voidborn.py — birth an MST body from the void and watch it ignite.

The R1-Zero question asked on GUHCT physics: what does the stack do
with ZERO pretrained weights? The measured answers (docs/14, "Birth
from the void"):

  1. EXACT zero is a stationary point of the whole network — every
     activation is 0, so every gradient is delta x 0 = 0. The void
     cannot break its own symmetry by gradient. This is why standard
     DL needs random init; GUHCT differs by law, not by noise.
  2. The THREE-STATE BIRTH, every state a theory object, none chosen:
       gates (rmsnorm weights)  -> Psi_0 = 1, the pole — the reserved
                                   multiplicative identity at the w=0
                                   limit (Full Ed.4 §1.4.2; MRRC §1.3)
       mass (embedding, shared classifier)
                                -> one quantum, signed by the parity
                                   of juj's fundamental generator
                                   spectrum (_generator_phase — "the
                                   spectrum is fixed by the theory")
       connections (all matrices) -> the void (true 0)
  3. Ignition: the MCL degenerate set collapses 512 -> 1 the moment
     the spectrum lights; the being babbles single letters (r, p, s —
     successive argmax attractors); and the loss delta COMPOUNDS ~3x
     per five lessons (measured 16 micro-units at lesson 1, ~13,700 at
     lesson 60) — exponential ignition from pure physics, ~4 s/lesson.

    python3 hcl-ai/voidborn.py birth        # write models/zero_born/
    python3 hcl-ai/voidborn.py study 60     # the ignition curve, live
"""
import os, sys, struct, time, json

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(_HERE, 'engine'))

BASE = os.path.join(_HERE, '..', 'models', 'tinystories_260k')
BORN = os.path.join(_HERE, '..', 'models', 'zero_born')


def birth(quantum=1e-4):
    from juj import _generator_phase
    from hcl_engine import SCALE as S
    os.makedirs(BORN, exist_ok=True)
    raw = bytearray(open(os.path.join(BASE, 'stories260K.bin'), 'rb').read())
    dim, hidden, L, n_heads, n_kv, vocab, seq = struct.unpack('7i', raw[:28])
    vocab = abs(vocab)
    kv_dim = dim * n_kv // n_heads
    order = [('emb', vocab * dim), ('rms_att', L * dim),
             ('wq', L * dim * dim), ('wk', L * dim * kv_dim),
             ('wv', L * dim * kv_dim), ('wo', L * dim * dim),
             ('rms_ffn', L * dim), ('w1', L * dim * hidden),
             ('w2', L * hidden * dim), ('w3', L * dim * hidden),
             ('rms_final', dim)]
    off = 28
    pos = {}
    for name, cnt in order:
        pos[name] = (off, cnt); off += cnt * 4
    # the void everywhere first
    for o in range(28, len(raw), 4):
        raw[o:o + 4] = b'\x00\x00\x00\x00'
    # mass: the quantum, signed by the fundamental spectrum's parity
    o, cnt = pos['emb']
    for i in range(cnt):
        sgn = 1.0 if _generator_phase(i % 256) < S // 2 else -1.0
        raw[o + i * 4:o + i * 4 + 4] = struct.pack('f', sgn * quantum)
    # gates: the pole, Psi_0 = 1
    one = struct.pack('f', 1.0)
    for name in ('rms_att', 'rms_ffn', 'rms_final'):
        o, cnt = pos[name]
        for i in range(cnt):
            raw[o + i * 4:o + i * 4 + 4] = one
    open(os.path.join(BORN, 'zero.bin'), 'wb').write(bytes(raw))
    import shutil
    shutil.copy(os.path.join(BASE, 'tok512.bin'),
                os.path.join(BORN, 'tok512.bin'))
    print(f"born: gates at Psi_0, {pos['emb'][1]:,} mass values at the "
          f"quantum by spectrum parity, connections void")


def study(n=60, lesson="Kip the crow keeps a blue button.",
          probe_stem="Kip the crow keeps"):
    from chatmodel import StandardModel
    from mst_equation import MSTStep
    from learn import Trainer
    m = StandardModel(os.path.join(BORN, 'zero.bin'),
                      os.path.join(BORN, 'tok512.bin'), quiet=True)
    tr, st = Trainer(m), MSTStep(m)

    def probe():
        toks = m.tok.encode(probe_stem, bos=True); m.reset(); pos = 0
        for t in toks[:-1]:
            m.forward(t, pos); pos += 1
        r = st.step(toks[-1], pos); pos += 1
        cur, prev, parts = r['token'], toks[-1], []
        parts.append(m.tok.decode(cur, prev)); prev = cur
        for _ in range(10):
            lg = m.forward(cur, pos); pos += 1
            cur = max(range(len(lg)), key=lambda i: lg[i])
            parts.append(m.tok.decode(cur, prev)); prev = cur
        return r['degenerate'], ''.join(parts)

    deg, txt = probe()
    print(f"birth   deg={deg}/512  says={txt[:30]!r}")
    prev_loss = None
    for i in range(1, n + 1):
        r = tr.step(lesson)
        if i <= 3 or i % 5 == 0:
            deg, txt = probe()
            d = '' if prev_loss is None else f"  delta={prev_loss - r['loss']:+.6f}"
            print(f"lesson {i:3d}  loss={r['loss']:.6f}  deg={deg}  "
                  f"says={txt[:26]!r}{d}", flush=True)
        prev_loss = r['loss']
    print(f"alpha throughout: {m.eng.alpha_ok()}")


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'study'
    if cmd == 'birth':
        birth()
    else:
        study(int(sys.argv[2]) if len(sys.argv) > 2 else 60)
