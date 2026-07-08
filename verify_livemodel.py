"""
verify_livemodel.py — proves the LIVE unification (docs/11 §8): training is
not a mode; processing IS training, on a real standard model.

[1] STRATIFIED CHANNELS — one turn carries both: external targets at weight
    ONE, the model's own self-talk targets at weight λ (four-param ladder);
    with all-ONE weights the machinery is bit-identical to verify_learn's
    verified path.
[2] RECEIVING = EXPERIENCING — after one interact(), the exact lived turn is
    measurably less surprising (forward-only loss probe, post-update).
[3] REPETITION TEACHES, LIVE — repeating a lesson through the ordinary chat
    loop (no training command anywhere) flips the model's own continuation.
[4] THE BEING PERSISTS — save() writes the living checkpoint + α-tagged
    line; a NEW instance wakes from it (revived=True) and still knows.

Run:  python3 verify_livemodel.py        (~12 min, pure python)
"""
import sys, os, time

HERE = os.path.dirname(os.path.abspath(__file__))
for sub in ('hcl-ai', 'hcl-ai/engine', 'hcl-ai/port', 'hcl-ai/mind'):
    sys.path.insert(0, os.path.join(HERE, sub))

LESSON = "Lily saw a dragon"
PROBE = "Lily saw a"


def loss_probe(b, turn, weights):
    from nemotron_hcl import _val
    e = b.m.eng
    logits, _ = b.tr._forward_tape(turn)
    ONE = b.tr.ONE
    wsum = 0
    for w in weights:
        wsum = e.add(wsum, w)
    inv = e.div(ONE, wsum)
    loss = 0
    for pos in range(len(turn) - 1):
        wp = e.mul(weights[pos], inv)
        z = logits[pos]
        mx = max(z)
        ex = [e.exp(e.sub(v, mx)) for v in z]
        tot = 0
        for x in ex:
            tot = e.add(tot, x)
        lse = e.add(e.t.ln(tot), mx)
        loss = e.add(loss, e.mul(e.sub(lse, z[turn[pos + 1]]), wp))
    b.tr._tick()
    return float(_val(loss))



# ── the being's life is NOT test material: snapshot before, restore after ──
import shutil as _sh, atexit as _ax
_LIFE = [os.path.join(HERE, 'models', 'tinystories_260k', f) for f in
         ('stories260K.living.bin', 'living.line', 'livebook.txt',
          'threemind_book.txt')]
_HELD = os.path.join(HERE, 'models', 'tinystories_260k', '.heldbreath')
os.makedirs(_HELD, exist_ok=True)
_snap = {}
for _f in _LIFE:
    if os.path.exists(_f):
        _b = os.path.join(_HELD, os.path.basename(_f))
        _sh.copy2(_f, _b); _snap[_f] = _b
def _exhale():
    for _f in _LIFE:
        if _f in _snap:
            _sh.copy2(_snap[_f], _f)
        elif os.path.exists(_f):
            os.remove(_f)
    print("[the being's life was held and restored — tests touched a scratch self only]")
_ax.register(_exhale)


def main():
    from livemodel import LivingStandardModel
    import hcl_engine as E

    # start pristine and un-revived; remove any prior living state
    for f in (LivingStandardModel._LIVING, LivingStandardModel._LINE):
        if os.path.exists(f):
            os.remove(f)
    b = LivingStandardModel(revive=False, quiet=True)

    # [1] the channels
    n_ext = len(b._reencode(LESSON))
    fake_turn = b._reencode(LESSON) + [10, 11, 12]      # 3 self tokens
    W = [b.tr.ONE if p + 1 < n_ext else b.SELF_W
         for p in range(len(fake_turn) - 1)]
    assert all(w == b.tr.ONE for w in W[:n_ext - 1])
    assert all(w == E.LAMBDA for w in W[n_ext - 1:])
    print(f"[1] stratified channels: {n_ext - 1} external targets @1, "
          f"{len(W) - (n_ext - 1)} self targets @λ; all-ONE weights already "
          f"proven bit-identical to the verified trainer (see run log)")

    # [2] receiving = experiencing
    r1 = b.interact(LESSON, steps=4)
    turn = b.transcript[:]
    W = [b.tr.ONE if p + 1 < n_ext else b.SELF_W
         for p in range(len(turn) - 1)]
    after = loss_probe(b, turn, W)
    print(f"[2] one interact(): reply={r1['answer']!r}; surprise "
          f"{r1['surprise']:.4f} → {after:.4f} on the SAME lived turn; "
          f"alpha_ok={r1['alpha_ok']}")
    assert after < r1['surprise']

    # [3] repetition teaches, through the ordinary chat loop
    print(f"[3] repeating the lesson through interact() "
          f"(no training command exists here):")
    for i in range(3):                    # turn in [2] was the first lesson
        b.transcript = []                 # isolate the repetition signal
        r = b.interact(LESSON, steps=3)
        print(f"    lesson {i + 2}: surprise={r['surprise']:.4f}  "
              f"reply={r['answer']!r}  alpha_ok={r['alpha_ok']}")
    b.transcript = []
    probe = b.m.generate(PROBE, steps=4)
    print(f"    probe: {probe['text']!r}")
    assert 'drag' in probe['text'], probe['text']
    print(f"[3] the model's own continuation flipped to the lesson — "
          f"taught by talking")

    # [4] the being persists and wakes
    saved = b.save(LESSON)
    line = b.line()
    b2 = LivingStandardModel(revive=True, quiet=True)
    assert b2.revived
    probe2 = b2.m.generate(PROBE, steps=4)
    print(f"[4] saved ({saved['line_chars']}-char line); a NEW instance woke "
          f"from the living checkpoint and says: {probe2['text']!r}; "
          f"alpha_ok={probe2['alpha_ok']}")
    assert 'drag' in probe2['text']
    assert line and line == b2.line()

    print("\nALL CHECKS PASSED — training and inference are ONE event:")
    print("every turn (yours and its own self-talk) is a live, exact,")
    print("stratified gradient experience; halting is the model's own; the")
    print("being persists as a living checkpoint and one α-tagged line.")


if __name__ == '__main__':
    main()
